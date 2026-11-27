import pytest
import statistics
import time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app import schemas

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def preparar_banco():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _criar_usuario_aux(nome: str, email: str, chave_pix: str):
    resp = client.post(
        "/usuarios/",
        json={
            "nome": nome,
            "telefone": "89999998888",
            "email": email,
            "senha": "senha123",
            "chave_pix": chave_pix,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_cadastro_usuario_ocultacao_senha_e_bloqueio_duplicidade():
    # 1. Cadastra um usuário válido
    _criar_usuario_aux("Gabriel", "gabriel@rateiofacil.com", "pix-gabriel")

    # 2. Verifica se a listagem retorna o usuário sem expor a senha
    usuarios = client.get("/usuarios/").json()
    assert len(usuarios) == 1
    assert "senha" not in usuarios[0]
    assert "senha_hash" not in usuarios[0]

    # 3. Tentar cadastrar e-mail já existente deve falhar com HTTP 400
    resp_dup = client.post(
        "/usuarios/",
        json={
            "nome": "Outro Gabriel",
            "telefone": "89988887777",
            "email": "gabriel@rateiofacil.com",
            "senha": "senha123",
            "chave_pix": "outro@pix.com",
        },
    )
    assert resp_dup.status_code == 400


def test_amizades_e_restricao_membro_grupo():
    ana = _criar_usuario_aux("Ana", "ana@rep.com", "pix-ana")
    bruno = _criar_usuario_aux("Bruno", "bruno@rep.com", "pix-bruno")

    grupo_resp = client.post(
        "/grupos/", json={"nome": "República UFPI", "criador_id": ana["id"]}
    )
    assert grupo_resp.status_code == 201
    grupo_id = grupo_resp.json()["id"]

    # Tentar adicionar Bruno sem serem amigos deve falhar
    resp_sem_amizade = client.post(
        f"/grupos/{grupo_id}/membros",
        json={"usuario_id": bruno["id"], "solicitante_id": ana["id"]},
    )
    assert resp_sem_amizade.status_code == 400
    assert "amigos" in resp_sem_amizade.json()["detalhe"].lower()

    # Adicionar Bruno como amigo por e-mail e depois vincular ao grupo
    amizade_resp = client.post(
        f"/usuarios/{ana['id']}/amigos", json={"email": "bruno@rep.com"}
    )
    assert amizade_resp.status_code == 201

    resp_com_amizade = client.post(
        f"/grupos/{grupo_id}/membros",
        json={"usuario_id": bruno["id"], "solicitante_id": ana["id"]},
    )
    assert resp_com_amizade.status_code == 201
    assert len(resp_com_amizade.json()["membros"]) == 2


def test_rateio_despesa_extrato_e_simplificacao_pix():
    ana = _criar_usuario_aux("Ana", "ana@rep.com", "chave-pix-ana")
    bruno = _criar_usuario_aux("Bruno", "bruno@rep.com", "chave-pix-bruno")

    grupo_id = client.post(
        "/grupos/", json={"nome": "República Picos", "criador_id": ana["id"]}
    ).json()["id"]
    client.post(f"/grupos/{grupo_id}/membros", json={"usuario_id": bruno["id"]})

    # 1. Ana paga R$ 600,00 de Aluguel e divide igualmente com Bruno
    desp_resp = client.post(
        "/despesas/",
        json={
            "descricao": "Aluguel",
            "valor_total": 600.00,
            "grupo_id": grupo_id,
            "pagador_id": ana["id"],
            "tipo_divisao": schemas.TipoDivisao.IGUAL.value,
        },
    )
    assert desp_resp.status_code == 201
    assert desp_resp.json()["pagador_id"] == ana["id"]

    # 2. Extrato individual de Bruno mostra sua cota de R$ 300,00 e saldo devedor de -R$ 300,00
    extrato_bruno = client.get(
        f"/grupos/{grupo_id}/membros/{bruno['id']}/extrato"
    ).json()
    assert extrato_bruno["total_pago_por_mim"] == 0.00
    assert extrato_bruno["total_minhas_cotas_pagas"] == 300.00
    assert extrato_bruno["saldo_liquido_atual"] == -300.00
    assert len(extrato_bruno["itens"]) == 1
    assert extrato_bruno["itens"][0]["pagador_nome"] == "Ana"

    # 3. Resumo financeiro do grupo gera acerto simplificado de R$ 300,00 via PIX para Ana
    resumo = client.get(f"/grupos/{grupo_id}/resumo").json()
    assert resumo["total_despesas_grupo"] == 600.00
    assert len(resumo["acertos_simplificados"]) == 1
    assert resumo["acertos_simplificados"][0]["devedor_nome"] == "Bruno"
    assert resumo["acertos_simplificados"][0]["credor_nome"] == "Ana"
    assert resumo["acertos_simplificados"][0]["credor_chave_pix"] == "chave-pix-ana"
    assert resumo["acertos_simplificados"][0]["valor"] == 300.00

def test_rnf2_desempenho():

    # Cria 5 usuários usando a função auxiliar (inclui telefone)
    usuarios = [
        _criar_usuario_aux(f"Morador {i}", f"morador{i}@teste.com", f"pix{i}@teste.com")
        for i in range(5)
    ]
    ids = [u["id"] for u in usuarios]

    for i in range(1, 5):
        resp_amg = client.post(
            f"/usuarios/{ids[0]}/amigos",
            json={"email": f"morador{i}@teste.com"},
        )
        assert resp_amg.status_code == 201

    grupo = client.post(
        "/grupos/",
        json={"nome": "Grupo Benchmark", "criador_id": ids[0]},
    ).json()
    for amigo_id in ids[1:]:
        resp_mb = client.post(
            f"/grupos/{grupo['id']}/membros",
            json={"usuario_id": amigo_id, "solicitante_id": ids[0]},
        )
        assert resp_mb.status_code == 201

    # Lança 50 despesas divididas igualmente entre os 5
    for i in range(50):
        resp_desp = client.post(
            "/despesas/",
            json={
                "descricao": f"Despesa {i}",
                "valor_total": 100.0,
                "grupo_id": grupo["id"],
                "pagador_id": ids[i % 5],
                "tipo_divisao": "IGUAL",
            },
        )
        assert resp_desp.status_code == 201

    tempos = []
    for _ in range(10):
        t = time.perf_counter()
        r = client.get(f"/grupos/{grupo['id']}/resumo")
        tempos.append((time.perf_counter() - t) * 1000)
        assert r.status_code == 200

    media_ms = statistics.mean(tempos)
    print(f"\n[RNF2] mín: {min(tempos):.1f} ms | média: {media_ms:.1f} ms | máx: {max(tempos):.1f} ms")
    assert media_ms < 1000