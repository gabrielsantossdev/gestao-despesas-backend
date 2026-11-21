from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app import models
from app.database import engine, Base
from app.services import RegraNegocioError, RecursoNaoEncontradoError
from app.controllers import usuarios_router, grupos_router, despesas_router

# Cria as tabelas no banco SQLite automaticamente na inicialização
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Gestão de Despesas Compartilhadas",
    description="API RESTful para divisão de contas, balanço de saldos e simplificação de dívidas.",
    version="1.0.0",
)


# TRATAMENTO GLOBAL DE EXCEÇÕES DE DOMÍNIO 
@app.exception_handler(RegraNegocioError)
async def regra_negocio_exception_handler(request: Request, exc: RegraNegocioError):
    return JSONResponse(
        status_code=400,
        content={"detalhe": str(exc)},
    )


@app.exception_handler(RecursoNaoEncontradoError)
async def recurso_nao_encontrado_exception_handler(
    request: Request, exc: RecursoNaoEncontradoError
):
    return JSONResponse(
        status_code=404,
        content={"detalhe": str(exc)},
    )


# REGISTRO DAS ROTAS MODULARES 
app.include_router(usuarios_router)
app.include_router(grupos_router)
app.include_router(despesas_router)


@app.get("/", tags=["Status"])
def verificar_status():
    return {
        "status": "online",
        "mensagem": "API de Gestão de Despesas Compartilhadas em funcionamento. Acesse /docs para testar.",
    }