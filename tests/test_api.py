import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app import schemas

# Banco SQLite em memória isolado para não sujar o banco principal durante os testes
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
    """Recria as tabelas limpas antes de cada teste."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _criar_usuario_aux(nome: str, email: str, cpf: str, chave_pix: str):
    resp = client.post(
        "/usuarios/",
        json={
            "nome": nome,
            "telefone": "89999998888",
            "email": email,
            "cpf": cpf,
            "senha": "senha123",
            "chave_pix": chave_pix,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_cadastro_usuario_e_bloqueio_duplicidade():
    u1 = _criar_usuario_aux("Ana Silva", "ana@email.com", "11122233344", "ana@pix.com")
    assert u1["nome"] == "Ana Silva"
    assert "senha" not in u1
    assert "senha_hash" not in u1

    # Tentar cadastrar mesmo e-mail deve retornar erro de regra de negócio (400)
    resp_dup = client.post(
        "/usuarios/",
        json={
            "nome": "Outra Ana",
            "telefone": "89988887777",
            "email": "ana@email.com",
            "cpf": "99988877766",
            "senha": "senha123",
            "chave_pix": "outra@pix.com",
        },
    )
    assert resp_dup.status_code == 400
    assert "e-mail" in resp_dup.json()["detalhe"].lower()


def test_fluxo_completo_divisao_e_simplificacao_dividas():
    # 1. Cadastrar 3 moradores
    ana = _criar_usuario_aux("Ana", "ana@rep.com", "11111111111", "chave-pix-ana")
    bruno = _criar_usuario_aux("Bruno", "bruno@rep.com", "22222222222", "chave-pix-bruno")
    carla = _criar_usuario_aux("Carla", "carla@rep.com", "33333333333", "chave-pix-carla")

    # 2. Criar grupo e adicionar os 3 membros
    grupo_resp = client.post("/grupos/", json={"nome": "República Picos"})
    assert grupo_resp.status_code == 201
    grupo_id = grupo_resp.json()["id"]

    for u in (ana, bruno, carla):
        add_resp = client.post(f"/grupos/{grupo_id}/membros", json={"usuario_id": u["id"]})
        assert add_resp.status_code == 201

    # 3. Ana paga R$ 300,00 de Aluguel dividido igualmente (R$ 100,00 para cada)
    desp1 = client.post(
        "/despesas/",
        json={
            "descricao": "Aluguel",
            "valor_total": 300.00,
            "grupo_id": grupo_id,
            "pagador_id": ana["id"],
            "tipo_divisao": schemas.TipoDivisao.IGUAL.value,
        },
    )
    assert desp1.status_code == 201

    # 4. Bruno paga R$ 150,00 de Internet dividido igualmente (R$ 50,00 para cada)
    desp2 = client.post(
        "/despesas/",
        json={
            "descricao": "Internet",
            "valor_total": 150.00,
            "grupo_id": grupo_id,
            "pagador_id": bruno["id"],
            "tipo_divisao": schemas.TipoDivisao.IGUAL.value,
        },
    )
    assert desp2.status_code == 201

    # Saldo esperado:
    # Total do grupo: R$ 450,00 (R$ 150,00 devido por pessoa)
    # Ana: pagou 300, deve 150 -> saldo +150,00 (credora)
    # Bruno: pagou 150, deve 150 -> saldo 0,00 (quitado)
    # Carla: pagou 0, deve 150 -> saldo -150,00 (devedora)
    # Simplificação: apenas 1 transferência (Carla -> Ana de R$ 150,00)
    resumo_resp = client.get(f"/grupos/{grupo_id}/resumo")
    assert resumo_resp.status_code == 200
    resumo = resumo_resp.json()

    assert resumo["total_despesas_grupo"] == 450.00
    assert len(resumo["acertos_simplificados"]) == 1

    acerto = resumo["acertos_simplificados"][0]
    assert acerto["devedor_nome"] == "Carla"
    assert acerto["credor_nome"] == "Ana"
    assert acerto["credor_chave_pix"] == "chave-pix-ana"
    assert acerto["valor"] == 150.00


def test_divisao_porcentagem_invalida_retorna_erro():
    ana = _criar_usuario_aux("Ana", "ana2@rep.com", "44444444444", "pix-ana2")
    bruno = _criar_usuario_aux("Bruno", "bruno2@rep.com", "55555555555", "pix-bruno2")

    grupo_id = client.post("/grupos/", json={"nome": "Viagem"}).json()["id"]
    client.post(f"/grupos/{grupo_id}/membros", json={"usuario_id": ana["id"]})
    client.post(f"/grupos/{grupo_id}/membros", json={"usuario_id": bruno["id"]})

    # Soma das porcentagens = 80% (deve falhar com HTTP 400)
    resp = client.post(
        "/despesas/",
        json={
            "descricao": "Combustível",
            "valor_total": 200.00,
            "grupo_id": grupo_id,
            "pagador_id": ana["id"],
            "tipo_divisao": schemas.TipoDivisao.PORCENTAGEM.value,
            "divisoes": [
                {"usuario_id": ana["id"], "percentual": 50.0},
                {"usuario_id": bruno["id"], "percentual": 30.0},
            ],
        },
    )
    assert resp.status_code == 400
    assert "100%" in resp.json()["detalhe"]