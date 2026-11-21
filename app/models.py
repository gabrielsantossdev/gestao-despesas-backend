from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    telefone = Column(String(20), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    cpf = Column(String(14), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    chave_pix = Column(String(120), nullable=False)  # Atende ao RF6 (Central de Acerto com PIX)

    grupos_associados = relationship("GrupoMembro", back_populates="usuario", cascade="all, delete-orphan")
    despesas_pagas = relationship("Despesa", back_populates="pagador")
    divisoes = relationship("Divisao", back_populates="usuario")


class Grupo(Base):
    __tablename__ = "grupos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    membros = relationship("GrupoMembro", back_populates="grupo", cascade="all, delete-orphan")
    despesas = relationship("Despesa", back_populates="grupo", cascade="all, delete-orphan")


class GrupoMembro(Base):
    __tablename__ = "grupo_membros"
    __table_args__ = (
        UniqueConstraint("usuario_id", "grupo_id", name="uq_usuario_grupo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    grupo_id = Column(Integer, ForeignKey("grupos.id", ondelete="CASCADE"), nullable=False)

    usuario = relationship("Usuario", back_populates="grupos_associados")
    grupo = relationship("Grupo", back_populates="membros")


class Despesa(Base):
    __tablename__ = "despesas"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String(150), nullable=False)
    valor_total = Column(Float, nullable=False)
    dia_compra = Column(Date, default=date.today, nullable=False)
    dia_vencimento = Column(Date, nullable=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id", ondelete="CASCADE"), index=True, nullable=False)
    pagador_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)

    grupo = relationship("Grupo", back_populates="despesas")
    pagador = relationship("Usuario", back_populates="despesas_pagas")
    divisoes = relationship("Divisao", back_populates="despesa", cascade="all, delete-orphan")


class Divisao(Base):
    __tablename__ = "divisoes"

    id = Column(Integer, primary_key=True, index=True)
    despesa_id = Column(Integer, ForeignKey("despesas.id", ondelete="CASCADE"), index=True, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    valor_devido = Column(Float, nullable=False)
    percentual = Column(Float, nullable=True)

    despesa = relationship("Despesa", back_populates="divisoes")
    usuario = relationship("Usuario", back_populates="divisoes")