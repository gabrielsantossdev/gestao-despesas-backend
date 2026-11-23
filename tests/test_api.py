import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.seed import popular_dados_iniciais
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


def test_seed_idempotente_e_bloqueio_duplicidade():
    with TestingSessionLocal() as db:
        popular_dados_iniciais(db)
        popular_dados_iniciais(db)  # Segunda chamada não deve duplicar

    usuarios = client.get("/usuarios/").json()
    assert len(usuarios) == 4
    assert "senha" not in usuarios[0]
    assert "senha_hash" not in usuarios[0]

    # Tentar cadastrar e-mail já existente deve falhar com HTTP 400
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


def test_despesa_pendente_quitacao_e_extrato_individual():
    ana = _criar_usuario_aux("Ana", "ana@rep.com", "chave-pix-ana")
    bruno = _criar_usuario_aux("Bruno", "bruno@rep.com", "chave-pix-bruno")

    grupo_id = client.post(
        "/grupos/", json={"nome": "República Picos", "criador_id": ana["id"]}
    ).json()["id"]
    client.post(f"/grupos/{grupo_id}/membros", json={"usuario_id": bruno["id"]})

    # 1. Cadastrar Aluguel de R$ 600 como PENDENTE (ninguém pagou ainda)
    desp_pend = client.post(
        "/despesas/",
        json={
            "descricao": "Aluguel",
            "valor_total": 600.00,
            "status": schemas.StatusDespesa.PENDENTE.value,
            "grupo_id": grupo_id,
            "tipo_divisao": schemas.TipoDivisao.IGUAL.value,
        },
    )
    assert desp_pend.status_code == 201
    despesa_id = desp_pend.json()["id"]

    # Enquanto pendente, não gera dívida de PIX entre Ana e Bruno
    resumo_antes = client.get(f"/grupos/{grupo_id}/resumo").json()
    assert resumo_antes["total_despesas_grupo"] == 0.0
    assert resumo_antes["total_pendente_grupo"] == 600.00
    assert len(resumo_antes["acertos_simplificados"]) == 0

    # Extrato do Bruno mostra R$ 300,00 pendentes a pagar
    extrato_bruno_antes = client.get(
        f"/grupos/{grupo_id}/membros/{bruno['id']}/extrato"
    ).json()
    assert extrato_bruno_antes["total_pendente_a_pagar"] == 300.00
    assert extrato_bruno_antes["saldo_liquido_atual"] == 0.00

    # 2. Ana quita o aluguel -> agora Bruno deve R$ 300,00 via PIX para Ana
    quitar_resp = client.patch(
        f"/despesas/{despesa_id}/pagar", json={"pagador_id": ana["id"]}
    )
    assert quitar_resp.status_code == 200
    assert quitar_resp.json()["status"] == "PAGA"

    resumo_depois = client.get(f"/grupos/{grupo_id}/resumo").json()
    assert resumo_depois["total_despesas_grupo"] == 600.00
    assert resumo_depois["total_pendente_grupo"] == 0.00
    assert len(resumo_depois["acertos_simplificados"]) == 1
    assert resumo_depois["acertos_simplificados"][0]["devedor_nome"] == "Bruno"
    assert resumo_depois["acertos_simplificados"][0]["credor_nome"] == "Ana"
    assert resumo_depois["acertos_simplificados"][0]["valor"] == 300.00