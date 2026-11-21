from typing import List, Optional
from sqlalchemy.orm import Session
from app import models, schemas


class UsuarioRepository:
    @staticmethod
    def criar(db: Session, dados: schemas.UsuarioCreate, senha_hash: str) -> models.Usuario:
        novo_usuario = models.Usuario(
            nome=dados.nome,
            telefone=dados.telefone,
            email=dados.email,
            cpf=dados.cpf,
            senha_hash=senha_hash,
            chave_pix=dados.chave_pix,
        )
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)
        return novo_usuario

    @staticmethod
    def buscar_por_id(db: Session, usuario_id: int) -> Optional[models.Usuario]:
        return db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

    @staticmethod
    def buscar_por_email(db: Session, email: str) -> Optional[models.Usuario]:
        return db.query(models.Usuario).filter(models.Usuario.email == email).first()

    @staticmethod
    def buscar_por_cpf(db: Session, cpf: str) -> Optional[models.Usuario]:
        return db.query(models.Usuario).filter(models.Usuario.cpf == cpf).first()

    @staticmethod
    def listar_todos(db: Session) -> List[models.Usuario]:
        return db.query(models.Usuario).all()

    @staticmethod
    def atualizar(db: Session, usuario: models.Usuario, dados: schemas.UsuarioUpdate) -> models.Usuario:
        if dados.nome is not None:
            usuario.nome = dados.nome
        if dados.telefone is not None:
            usuario.telefone = dados.telefone
        if dados.chave_pix is not None:
            usuario.chave_pix = dados.chave_pix
        db.commit()
        db.refresh(usuario)
        return usuario

    @staticmethod
    def deletar(db: Session, usuario: models.Usuario) -> None:
        db.delete(usuario)
        db.commit()


class GrupoRepository:
    @staticmethod
    def criar(db: Session, nome: str) -> models.Grupo:
        novo_grupo = models.Grupo(nome=nome)
        db.add(novo_grupo)
        db.commit()
        db.refresh(novo_grupo)
        return novo_grupo

    @staticmethod
    def buscar_por_id(db: Session, grupo_id: int) -> Optional[models.Grupo]:
        return db.query(models.Grupo).filter(models.Grupo.id == grupo_id).first()

    @staticmethod
    def listar_todos(db: Session) -> List[models.Grupo]:
        return db.query(models.Grupo).all()

    @staticmethod
    def atualizar(db: Session, grupo: models.Grupo, nome: str) -> models.Grupo:
        grupo.nome = nome
        db.commit()
        db.refresh(grupo)
        return grupo

    @staticmethod
    def deletar(db: Session, grupo: models.Grupo) -> None:
        db.delete(grupo)
        db.commit()

    @staticmethod
    def buscar_vinculo_membro(db: Session, grupo_id: int, usuario_id: int) -> Optional[models.GrupoMembro]:
        return (
            db.query(models.GrupoMembro)
            .filter(
                models.GrupoMembro.grupo_id == grupo_id,
                models.GrupoMembro.usuario_id == usuario_id,
            )
            .first()
        )

    @staticmethod
    def adicionar_membro(db: Session, grupo_id: int, usuario_id: int) -> models.GrupoMembro:
        vinculo = models.GrupoMembro(grupo_id=grupo_id, usuario_id=usuario_id)
        db.add(vinculo)
        db.commit()
        db.refresh(vinculo)
        return vinculo

    @staticmethod
    def remover_membro(db: Session, vinculo: models.GrupoMembro) -> None:
        db.delete(vinculo)
        db.commit()


class DespesaRepository:
    @staticmethod
    def criar_com_divisoes(
        db: Session,
        despesa: models.Despesa,
        divisoes: List[models.Divisao],
    ) -> models.Despesa:
        """
        Salva a despesa e todas as suas divisões em uma única transação atômica.
        Se qualquer falha ocorrer, desfaz tudo (rollback) garantindo integridade dos dados.
        """
        try:
            db.add(despesa)
            db.flush()  # Gera o despesa.id antes de finalizar a transação
            for div in divisoes:
                div.despesa_id = despesa.id
                db.add(div)
            db.commit()
            db.refresh(despesa)
            return despesa
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def buscar_por_id(db: Session, despesa_id: int) -> Optional[models.Despesa]:
        return db.query(models.Despesa).filter(models.Despesa.id == despesa_id).first()

    @staticmethod
    def listar_por_grupo(db: Session, grupo_id: int) -> List[models.Despesa]:
        return db.query(models.Despesa).filter(models.Despesa.grupo_id == grupo_id).all()

    @staticmethod
    def atualizar(db: Session, despesa: models.Despesa, dados: schemas.DespesaUpdate) -> models.Despesa:
        if dados.descricao is not None:
            despesa.descricao = dados.descricao
        if dados.dia_vencimento is not None:
            despesa.dia_vencimento = dados.dia_vencimento
        db.commit()
        db.refresh(despesa)
        return despesa

    @staticmethod
    def deletar(db: Session, despesa: models.Despesa) -> None:
        db.delete(despesa)
        db.commit()