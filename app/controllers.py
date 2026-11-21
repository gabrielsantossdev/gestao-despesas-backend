from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app import schemas
from app.database import get_db
from app.services import UsuarioService, GrupoService, DespesaService

usuarios_router = APIRouter(prefix="/usuarios", tags=["Usuários"])
grupos_router = APIRouter(prefix="/grupos", tags=["Grupos"])
despesas_router = APIRouter(prefix="/despesas", tags=["Despesas"])


#  ROTAS DE USUÁRIOS (RF1 e RF6) 
@usuarios_router.post(
    "/",
    response_model=schemas.UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo usuário",
)
def criar_usuario(dados: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    return UsuarioService.criar_usuario(db, dados)


@usuarios_router.get(
    "/",
    response_model=List[schemas.UsuarioResponse],
    summary="Listar todos os usuários",
)
def listar_usuarios(db: Session = Depends(get_db)):
    return UsuarioService.listar_usuarios(db)


@usuarios_router.get(
    "/{usuario_id}",
    response_model=schemas.UsuarioResponse,
    summary="Buscar usuário por ID",
)
def obter_usuario(usuario_id: int, db: Session = Depends(get_db)):
    return UsuarioService.obter_usuario(db, usuario_id)


@usuarios_router.put(
    "/{usuario_id}",
    response_model=schemas.UsuarioResponse,
    summary="Atualizar dados ou chave PIX do usuário",
)
def atualizar_usuario(
    usuario_id: int, dados: schemas.UsuarioUpdate, db: Session = Depends(get_db)
):
    return UsuarioService.atualizar_usuario(db, usuario_id, dados)


@usuarios_router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover usuário",
)
def deletar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    UsuarioService.deletar_usuario(db, usuario_id)


#  ROTAS DE GRUPOS E BALANÇO FINANCEIRO (RF1, RF4, RF5 e RF6) 
@grupos_router.post(
    "/",
    response_model=schemas.GrupoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar novo grupo (república ou viagem)",
)
def criar_grupo(dados: schemas.GrupoCreate, db: Session = Depends(get_db)):
    return GrupoService.criar_grupo(db, dados)


@grupos_router.get(
    "/",
    response_model=List[schemas.GrupoResponse],
    summary="Listar todos os grupos",
)
def listar_grupos(db: Session = Depends(get_db)):
    return GrupoService.listar_grupos(db)


@grupos_router.get(
    "/{grupo_id}",
    response_model=schemas.GrupoResponse,
    summary="Obter detalhes e membros de um grupo",
)
def obter_grupo(grupo_id: int, db: Session = Depends(get_db)):
    return GrupoService.obter_grupo(db, grupo_id)


@grupos_router.post(
    "/{grupo_id}/membros",
    response_model=schemas.GrupoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar morador/participante ao grupo",
)
def adicionar_membro(
    grupo_id: int, dados: schemas.MembroAdd, db: Session = Depends(get_db)
):
    return GrupoService.adicionar_membro(db, grupo_id, dados.usuario_id)


@grupos_router.delete(
    "/{grupo_id}/membros/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover morador/participante do grupo",
)
def remover_membro(grupo_id: int, usuario_id: int, db: Session = Depends(get_db)):
    GrupoService.remover_membro(db, grupo_id, usuario_id)


@grupos_router.delete(
    "/{grupo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir grupo",
)
def deletar_grupo(grupo_id: int, db: Session = Depends(get_db)):
    GrupoService.deletar_grupo(db, grupo_id)


@grupos_router.get(
    "/{grupo_id}/resumo",
    response_model=schemas.ResumoFinanceiroGrupo,
    summary="Gerar balanço de saldos, simplificação de dívidas e chaves PIX",
)
def obter_resumo_financeiro(grupo_id: int, db: Session = Depends(get_db)):
    return DespesaService.calcular_resumo_financeiro(db, grupo_id)


#  ROTAS DE DESPESAS (RF2 e RF3)
@despesas_router.post(
    "/",
    response_model=schemas.DespesaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar despesa com divisão igualitária, exata ou percentual",
)
def registrar_despesa(dados: schemas.DespesaCreate, db: Session = Depends(get_db)):
    return DespesaService.registrar_despesa(db, dados)


@despesas_router.get(
    "/grupo/{grupo_id}",
    response_model=List[schemas.DespesaResponse],
    summary="Listar todas as despesas de um grupo",
)
def listar_despesas_grupo(grupo_id: int, db: Session = Depends(get_db)):
    return DespesaService.listar_despesas_grupo(db, grupo_id)


@despesas_router.put(
    "/{despesa_id}",
    response_model=schemas.DespesaResponse,
    summary="Atualizar descrição ou vencimento da despesa",
)
def atualizar_despesa(
    despesa_id: int, dados: schemas.DespesaUpdate, db: Session = Depends(get_db)
):
    return DespesaService.atualizar_despesa(db, despesa_id, dados)


@despesas_router.delete(
    "/{despesa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir despesa",
)
def deletar_despesa(despesa_id: int, db: Session = Depends(get_db)):
    DespesaService.deletar_despesa(db, despesa_id)