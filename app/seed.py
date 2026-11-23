from sqlalchemy.orm import Session
from app import schemas
from app.repositories import UsuarioRepository, AmizadeRepository
from app.services import UsuarioService


USUARIOS_INICIAIS = [
    {
        "nome": "Gabriel Santos",
        "telefone": "89999001111",
        "email": "gabriel@rateiofacil.com",
        "senha": "1234",
        "chave_pix": "gabriel@pix.com",
    },
    {
        "nome": "João Hitalo",
        "telefone": "89999002222",
        "email": "joao@rateiofacil.com",
        "senha": "1234",
        "chave_pix": "joao@pix.com",
    },
    {
        "nome": "Ana Clara",
        "telefone": "89999003333",
        "email": "ana@rateiofacil.com",
        "senha": "1234",
        "chave_pix": "89999003333",
    },
    {
        "nome": "Lucas Mendes",
        "telefone": "89999004444",
        "email": "lucas@rateiofacil.com",
        "senha": "1234",
        "chave_pix": "lucas.mendes@pix.com",
    },
]


def popular_dados_iniciais(db: Session) -> None:
    """
    Popula o banco SQLite com 4 usuários pré-cadastrados para demonstrar o fluxo
    de adição de amigos sem necessidade de tela de auto-cadastro no MVP.
    Execução idempotente: não duplica registros se já existirem.
    """
    criados = []
    for item in USUARIOS_INICIAIS:
        existente = UsuarioRepository.buscar_por_email(db, item["email"])
        if not existente:
            existente = UsuarioService.criar_usuario(db, schemas.UsuarioCreate(**item))
        criados.append(existente)

    # Deixa Gabriel e João já conectados como amigos iniciais, mantendo Ana e Lucas
    # disponíveis no catálogo para demonstrar a adição de amigos ao vivo.
    if len(criados) >= 2:
        AmizadeRepository.criar_vinculo_bidirecional(db, criados[0].id, criados[1].id)