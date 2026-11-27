from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# ENUMS
class TipoDivisao(str, Enum):
    IGUAL = "IGUAL"
    EXATA = "EXATA"
    PORCENTAGEM = "PORCENTAGEM"


# SCHEMAS DE USUÁRIO E AMIZADES (RF1, RF6 e RF8)
class UsuarioCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    telefone: str = Field(..., min_length=8, max_length=20)
    email: EmailStr
    senha: str = Field(..., min_length=4)
    chave_pix: str = Field(..., min_length=3, max_length=120)


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    telefone: Optional[str] = Field(None, min_length=8, max_length=20)
    chave_pix: Optional[str] = Field(None, min_length=3, max_length=120)


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    telefone: str
    email: EmailStr
    chave_pix: str

    class Config:
        from_attributes = True


class AmigoAdd(BaseModel):
    amigo_id: Optional[int] = None
    email: Optional[EmailStr] = None


# SCHEMAS DE GRUPO (RF1 e RF8)
class GrupoCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    criador_id: Optional[int] = None


class MembroAdd(BaseModel):
    usuario_id: int
    solicitante_id: Optional[int] = None


class GrupoResponse(BaseModel):
    id: int
    nome: str
    criado_em: datetime
    membros: List[UsuarioResponse] = []

    class Config:
        from_attributes = True


# SCHEMAS DE DESPESAS E DIVISÃO (RF2 e RF3)
class DivisaoInput(BaseModel):
    usuario_id: int
    valor_devido: Optional[float] = Field(None, ge=0)
    percentual: Optional[float] = Field(None, ge=0, le=100)


class DespesaCreate(BaseModel):
    descricao: str = Field(..., min_length=2, max_length=150)
    valor_total: float = Field(..., gt=0, description="O valor da despesa deve ser maior que zero")
    dia_compra: Optional[date] = None
    dia_vencimento: Optional[date] = None
    grupo_id: int
    pagador_id: int
    tipo_divisao: TipoDivisao = TipoDivisao.IGUAL
    divisoes: Optional[List[DivisaoInput]] = None


class DespesaUpdate(BaseModel):
    descricao: Optional[str] = Field(None, min_length=2, max_length=150)
    dia_vencimento: Optional[date] = None


class DivisaoResponse(BaseModel):
    id: int
    usuario_id: int
    valor_devido: float
    percentual: Optional[float] = None

    class Config:
        from_attributes = True


class DespesaResponse(BaseModel):
    id: int
    descricao: str
    valor_total: float
    dia_compra: date
    dia_vencimento: Optional[date] = None
    grupo_id: int
    pagador_id: int
    divisoes: List[DivisaoResponse] = []

    class Config:
        from_attributes = True


# SCHEMAS DE SALDOS, EXTRATO INDIVIDUAL E SIMPLIFICAÇÃO DE DÍVIDAS (RF4, RF5, RF6 e RF9)
class SaldoUsuario(BaseModel):
    usuario_id: int
    nome: str
    total_pago: float
    total_devido: float
    saldo_liquido: float


class SugestaoAcerto(BaseModel):
    devedor_id: int
    devedor_nome: str
    credor_id: int
    credor_nome: str
    credor_chave_pix: str
    valor: float


class ResumoFinanceiroGrupo(BaseModel):
    grupo_id: int
    grupo_nome: str
    total_despesas_grupo: float
    saldos: List[SaldoUsuario]
    acertos_simplificados: List[SugestaoAcerto]


class ItemExtratoMembro(BaseModel):
    despesa_id: int
    descricao: str
    dia_compra: date
    dia_vencimento: Optional[date] = None
    valor_total_despesa: float
    pagador_id: int
    pagador_nome: str
    minha_cota: float
    percentual: Optional[float] = None
    eu_paguei: bool
    saldo_na_despesa: float


class ExtratoMembroGrupo(BaseModel):
    grupo_id: int
    grupo_nome: str
    usuario_id: int
    usuario_nome: str
    total_pago_por_mim: float
    total_minhas_cotas_pagas: float
    saldo_liquido_atual: float
    itens: List[ItemExtratoMembro]