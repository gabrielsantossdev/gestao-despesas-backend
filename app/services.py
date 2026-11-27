import hashlib
from datetime import date
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app import models, schemas
from app.repositories import (
    UsuarioRepository,
    AmizadeRepository,
    GrupoRepository,
    DespesaRepository,
)


# EXCEÇÕES DE DOMÍNIO (Desacopladas do protocolo HTTP / RNF4)
class RegraNegocioError(Exception):
    pass


class RecursoNaoEncontradoError(Exception):
    pass


# SERVIÇO DE USUÁRIOS (RF1 e RF6)
class UsuarioService:
    @staticmethod
    def _gerar_hash_senha(senha: str) -> str:
        return hashlib.sha256(senha.encode("utf-8")).hexdigest()

    @staticmethod
    def criar_usuario(db: Session, dados: schemas.UsuarioCreate) -> models.Usuario:
        if UsuarioRepository.buscar_por_email(db, dados.email):
            raise RegraNegocioError("Já existe um usuário cadastrado com este e-mail.")

        senha_hash = UsuarioService._gerar_hash_senha(dados.senha)
        return UsuarioRepository.criar(db, dados, senha_hash)

    @staticmethod
    def obter_usuario(db: Session, usuario_id: int) -> models.Usuario:
        usuario = UsuarioRepository.buscar_por_id(db, usuario_id)
        if not usuario:
            raise RecursoNaoEncontradoError(f"Usuário com ID {usuario_id} não encontrado.")
        return usuario

    @staticmethod
    def listar_usuarios(db: Session) -> List[models.Usuario]:
        return UsuarioRepository.listar_todos(db)

    @staticmethod
    def atualizar_usuario(db: Session, usuario_id: int, dados: schemas.UsuarioUpdate) -> models.Usuario:
        usuario = UsuarioService.obter_usuario(db, usuario_id)
        return UsuarioRepository.atualizar(db, usuario, dados)

    @staticmethod
    def deletar_usuario(db: Session, usuario_id: int) -> None:
        usuario = UsuarioService.obter_usuario(db, usuario_id)
        UsuarioRepository.deletar(db, usuario)


# SERVIÇO DE AMIZADES (RF8)
class AmizadeService:
    @staticmethod
    def adicionar_amigo(db: Session, usuario_id: int, dados: schemas.AmigoAdd) -> models.Usuario:
        UsuarioService.obter_usuario(db, usuario_id)

        amigo: Optional[models.Usuario] = None
        if dados.amigo_id is not None:
            amigo = UsuarioService.obter_usuario(db, dados.amigo_id)
        elif dados.email is not None:
            amigo = UsuarioRepository.buscar_por_email(db, dados.email)
            if not amigo:
                raise RecursoNaoEncontradoError(f"Nenhum usuário encontrado com o e-mail {dados.email}.")
        else:
            raise RegraNegocioError("Informe o ID ou o e-mail do amigo para adicionar.")

        if amigo.id == usuario_id:
            raise RegraNegocioError("Você não pode adicionar a si mesmo como amigo.")

        if AmizadeRepository.buscar_vinculo(db, usuario_id, amigo.id):
            raise RegraNegocioError(f"{amigo.nome} já está na sua lista de amigos.")

        AmizadeRepository.criar_vinculo_bidirecional(db, usuario_id, amigo.id)
        return amigo

    @staticmethod
    def listar_amigos(db: Session, usuario_id: int) -> List[models.Usuario]:
        UsuarioService.obter_usuario(db, usuario_id)
        return AmizadeRepository.listar_amigos(db, usuario_id)

    @staticmethod
    def sao_amigos(db: Session, usuario_id: int, amigo_id: int) -> bool:
        return AmizadeRepository.buscar_vinculo(db, usuario_id, amigo_id) is not None

    @staticmethod
    def remover_amigo(db: Session, usuario_id: int, amigo_id: int) -> None:
        UsuarioService.obter_usuario(db, usuario_id)
        UsuarioService.obter_usuario(db, amigo_id)
        AmizadeRepository.remover_vinculo_bidirecional(db, usuario_id, amigo_id)


# SERVIÇO DE GRUPOS E MORADORES (RF1 e RF8)
class GrupoService:
    @staticmethod
    def _formatar_resposta(grupo: models.Grupo) -> schemas.GrupoResponse:
        usuarios_membros = [vinculo.usuario for vinculo in grupo.membros]
        return schemas.GrupoResponse(
            id=grupo.id,
            nome=grupo.nome,
            criado_em=grupo.criado_em,
            membros=usuarios_membros,
        )

    @staticmethod
    def criar_grupo(db: Session, dados: schemas.GrupoCreate) -> schemas.GrupoResponse:
        if dados.criador_id is not None:
            UsuarioService.obter_usuario(db, dados.criador_id)

        grupo = GrupoRepository.criar(db, dados.nome)

        if dados.criador_id is not None:
            GrupoRepository.adicionar_membro(db, grupo.id, dados.criador_id)
            db.refresh(grupo)

        return GrupoService._formatar_resposta(grupo)

    @staticmethod
    def obter_grupo_model(db: Session, grupo_id: int) -> models.Grupo:
        grupo = GrupoRepository.buscar_por_id(db, grupo_id)
        if not grupo:
            raise RecursoNaoEncontradoError(f"Grupo com ID {grupo_id} não encontrado.")
        return grupo

    @staticmethod
    def obter_grupo(db: Session, grupo_id: int) -> schemas.GrupoResponse:
        grupo = GrupoService.obter_grupo_model(db, grupo_id)
        return GrupoService._formatar_resposta(grupo)

    @staticmethod
    def listar_grupos(db: Session) -> List[schemas.GrupoResponse]:
        grupos = GrupoRepository.listar_todos(db)
        return [GrupoService._formatar_resposta(g) for g in grupos]

    @staticmethod
    def adicionar_membro(
        db: Session,
        grupo_id: int,
        usuario_id: int,
        solicitante_id: Optional[int] = None,
    ) -> schemas.GrupoResponse:
        grupo = GrupoService.obter_grupo_model(db, grupo_id)
        UsuarioService.obter_usuario(db, usuario_id)

        if solicitante_id is not None and solicitante_id != usuario_id:
            if not AmizadeService.sao_amigos(db, solicitante_id, usuario_id):
                raise RegraNegocioError(
                    "Você só pode adicionar ao grupo usuários que estejam na sua lista de amigos."
                )

        if GrupoRepository.buscar_vinculo_membro(db, grupo_id, usuario_id):
            raise RegraNegocioError("Este usuário já faz parte do grupo.")

        GrupoRepository.adicionar_membro(db, grupo_id, usuario_id)
        db.refresh(grupo)
        return GrupoService._formatar_resposta(grupo)

    @staticmethod
    def remover_membro(db: Session, grupo_id: int, usuario_id: int) -> None:
        GrupoService.obter_grupo_model(db, grupo_id)
        vinculo = GrupoRepository.buscar_vinculo_membro(db, grupo_id, usuario_id)
        if not vinculo:
            raise RecursoNaoEncontradoError("Vínculo de membro não encontrado neste grupo.")
        GrupoRepository.remover_membro(db, vinculo)

    @staticmethod
    def deletar_grupo(db: Session, grupo_id: int) -> None:
        grupo = GrupoService.obter_grupo_model(db, grupo_id)
        GrupoRepository.deletar(db, grupo)


# SERVIÇO DE DESPESAS, EXTRATO E SIMPLIFICAÇÃO (RF2 a RF6, RF10)
class DespesaService:
    @staticmethod
    def _calcular_divisoes(
        dados: schemas.DespesaCreate,
        membros_ids: List[int],
    ) -> List[models.Divisao]:
        if not membros_ids:
            raise RegraNegocioError("O grupo não possui moradores cadastrados para dividir a despesa.")

        if dados.pagador_id not in membros_ids:
            raise RegraNegocioError("O usuário pagador precisa ser um membro do grupo.")

        divisoes_models: List[models.Divisao] = []

        # 1. DIVISÃO IGUALITÁRIA
        if dados.tipo_divisao == schemas.TipoDivisao.IGUAL:
            participantes = (
                [d.usuario_id for d in dados.divisoes]
                if dados.divisoes
                else membros_ids
            )
            if not participantes:
                raise RegraNegocioError("Nenhum participante informado para a divisão.")

            for uid in participantes:
                if uid not in membros_ids:
                    raise RegraNegocioError(f"O usuário {uid} não pertence ao grupo.")

            qtd = len(participantes)
            valor_base = round(dados.valor_total / qtd, 2)
            percentual_base = round(100.0 / qtd, 2)
            acumulado = 0.0

            for i, uid in enumerate(participantes):
                if i == qtd - 1:
                    valor_final = round(dados.valor_total - acumulado, 2)
                else:
                    valor_final = valor_base
                    acumulado = round(acumulado + valor_final, 2)

                divisoes_models.append(
                    models.Divisao(
                        usuario_id=uid,
                        valor_devido=valor_final,
                        percentual=percentual_base,
                    )
                )

        # 2. DIVISÃO POR VALORES EXATOS
        elif dados.tipo_divisao == schemas.TipoDivisao.EXATA:
            if not dados.divisoes:
                raise RegraNegocioError("Informe a lista de divisões com os valores exatos.")

            soma_valores = 0.0
            for item in dados.divisoes:
                if item.usuario_id not in membros_ids:
                    raise RegraNegocioError(f"O usuário {item.usuario_id} não pertence ao grupo.")
                if item.valor_devido is None:
                    raise RegraNegocioError("O campo valor_devido é obrigatório na divisão exata.")

                soma_valores += item.valor_devido
                percentual_calc = round((item.valor_devido / dados.valor_total) * 100, 2)
                divisoes_models.append(
                    models.Divisao(
                        usuario_id=item.usuario_id,
                        valor_devido=round(item.valor_devido, 2),
                        percentual=percentual_calc,
                    )
                )

            if abs(soma_valores - dados.valor_total) > 0.01:
                raise RegraNegocioError(
                    f"A soma dos valores divididos (R$ {soma_valores:.2f}) difere do total (R$ {dados.valor_total:.2f})."
                )

        # 3. DIVISÃO POR PORCENTAGEM
        elif dados.tipo_divisao == schemas.TipoDivisao.PORCENTAGEM:
            if not dados.divisoes:
                raise RegraNegocioError("Informe a lista de divisões com as porcentagens.")

            soma_percentuais = sum(item.percentual or 0.0 for item in dados.divisoes)
            if abs(soma_percentuais - 100.0) > 0.01:
                raise RegraNegocioError(
                    f"A soma das porcentagens ({soma_percentuais:.2f}%) deve ser igual a 100%."
                )

            acumulado = 0.0
            qtd = len(dados.divisoes)
            for i, item in enumerate(dados.divisoes):
                if item.usuario_id not in membros_ids:
                    raise RegraNegocioError(f"O usuário {item.usuario_id} não pertence ao grupo.")
                if item.percentual is None:
                    raise RegraNegocioError("O campo percentual é obrigatório na divisão por porcentagem.")

                if i == qtd - 1:
                    valor_final = round(dados.valor_total - acumulado, 2)
                else:
                    valor_final = round(dados.valor_total * (item.percentual / 100.0), 2)
                    acumulado = round(acumulado + valor_final, 2)

                divisoes_models.append(
                    models.Divisao(
                        usuario_id=item.usuario_id,
                        valor_devido=valor_final,
                        percentual=item.percentual,
                    )
                )

        return divisoes_models

    @staticmethod
    def registrar_despesa(db: Session, dados: schemas.DespesaCreate) -> models.Despesa:
        grupo = GrupoService.obter_grupo_model(db, dados.grupo_id)
        membros_ids = [m.usuario_id for m in grupo.membros]

        divisoes_models = DespesaService._calcular_divisoes(dados, membros_ids)

        nova_despesa = models.Despesa(
            descricao=dados.descricao,
            valor_total=round(dados.valor_total, 2),
            dia_compra=dados.dia_compra or date.today(),
            dia_vencimento=dados.dia_vencimento,
            grupo_id=dados.grupo_id,
            pagador_id=dados.pagador_id,
        )

        return DespesaRepository.criar_com_divisoes(db, nova_despesa, divisoes_models)

    @staticmethod
    def listar_despesas_grupo(db: Session, grupo_id: int) -> List[models.Despesa]:
        GrupoService.obter_grupo_model(db, grupo_id)
        return DespesaRepository.listar_por_grupo(db, grupo_id)

    @staticmethod
    def atualizar_despesa(
        db: Session, despesa_id: int, dados: schemas.DespesaUpdate
    ) -> models.Despesa:
        despesa = DespesaRepository.buscar_por_id(db, despesa_id)
        if not despesa:
            raise RecursoNaoEncontradoError(f"Despesa com ID {despesa_id} não encontrada.")
        return DespesaRepository.atualizar(db, despesa, dados)

    @staticmethod
    def deletar_despesa(db: Session, despesa_id: int) -> None:
        despesa = DespesaRepository.buscar_por_id(db, despesa_id)
        if not despesa:
            raise RecursoNaoEncontradoError(f"Despesa com ID {despesa_id} não encontrada.")
        DespesaRepository.deletar(db, despesa)

    @staticmethod
    def calcular_resumo_financeiro(db: Session, grupo_id: int) -> schemas.ResumoFinanceiroGrupo:
        grupo = GrupoService.obter_grupo_model(db, grupo_id)
        despesas = DespesaRepository.listar_por_grupo(db, grupo_id)

        usuarios_map: Dict[int, models.Usuario] = {
            m.usuario.id: m.usuario for m in grupo.membros
        }
        total_pago: Dict[int, float] = {uid: 0.0 for uid in usuarios_map}
        total_devido: Dict[int, float] = {uid: 0.0 for uid in usuarios_map}

        total_despesas_grupo = 0.0

        for despesa in despesas:
            total_despesas_grupo += despesa.valor_total
            if despesa.pagador_id in total_pago:
                total_pago[despesa.pagador_id] += despesa.valor_total

            for div in despesa.divisoes:
                if div.usuario_id in total_devido:
                    total_devido[div.usuario_id] += div.valor_devido

        saldos: List[schemas.SaldoUsuario] = []
        devedores = []
        credores = []

        for uid, usuario in usuarios_map.items():
            pago = round(total_pago[uid], 2)
            devido = round(total_devido[uid], 2)
            liquido = round(pago - devido, 2)

            saldos.append(
                schemas.SaldoUsuario(
                    usuario_id=uid,
                    nome=usuario.nome,
                    total_pago=pago,
                    total_devido=devido,
                    saldo_liquido=liquido,
                )
            )

            if liquido < -0.009:
                devedores.append([uid, usuario.nome, abs(liquido)])
            elif liquido > 0.009:
                credores.append([uid, usuario.nome, usuario.chave_pix, liquido])

        acertos: List[schemas.SugestaoAcerto] = []
        while devedores and credores:
            devedores.sort(key=lambda x: x[2], reverse=True)
            credores.sort(key=lambda x: x[3], reverse=True)

            maior_devedor = devedores[0]
            maior_credor = credores[0]

            valor_transferencia = round(min(maior_devedor[2], maior_credor[3]), 2)

            acertos.append(
                schemas.SugestaoAcerto(
                    devedor_id=maior_devedor[0],
                    devedor_nome=maior_devedor[1],
                    credor_id=maior_credor[0],
                    credor_nome=maior_credor[1],
                    credor_chave_pix=maior_credor[2],
                    valor=valor_transferencia,
                )
            )

            maior_devedor[2] = round(maior_devedor[2] - valor_transferencia, 2)
            maior_credor[3] = round(maior_credor[3] - valor_transferencia, 2)

            if maior_devedor[2] <= 0.009:
                devedores.pop(0)
            if maior_credor[3] <= 0.009:
                credores.pop(0)

        return schemas.ResumoFinanceiroGrupo(
            grupo_id=grupo.id,
            grupo_nome=grupo.nome,
            total_despesas_grupo=round(total_despesas_grupo, 2),
            saldos=saldos,
            acertos_simplificados=acertos,
        )

    @staticmethod
    def gerar_extrato_membro(
        db: Session, grupo_id: int, usuario_id: int
    ) -> schemas.ExtratoMembroGrupo:
        """
        RF10: Gera o extrato individualizado de um membro em um grupo, detalhando
        quanto ele deve em cada despesa e quem efetuou o pagamento.
        """
        grupo = GrupoService.obter_grupo_model(db, grupo_id)
        usuario = UsuarioService.obter_usuario(db, usuario_id)

        membros_map: Dict[int, models.Usuario] = {
            m.usuario.id: m.usuario for m in grupo.membros
        }
        if usuario_id not in membros_map:
            raise RegraNegocioError("Este usuário não participa do grupo selecionado.")

        despesas = DespesaRepository.listar_por_grupo(db, grupo_id)

        itens: List[schemas.ItemExtratoMembro] = []
        total_pago_por_mim = 0.0
        total_minhas_cotas_pagas = 0.0

        for despesa in despesas:
            minha_div = next(
                (d for d in despesa.divisoes if d.usuario_id == usuario_id), None
            )
            eu_paguei = despesa.pagador_id == usuario_id

            if not minha_div and not eu_paguei:
                continue

            minha_cota = round(minha_div.valor_devido, 2) if minha_div else 0.0
            percentual = minha_div.percentual if minha_div else 0.0

            pag_obj = membros_map.get(despesa.pagador_id)
            pagador_nome = pag_obj.nome if pag_obj else f"Usuário #{despesa.pagador_id}"

            valor_pago_nesta = despesa.valor_total if eu_paguei else 0.0
            saldo_item = round(valor_pago_nesta - minha_cota, 2)
            total_pago_por_mim = round(total_pago_por_mim + valor_pago_nesta, 2)
            total_minhas_cotas_pagas = round(total_minhas_cotas_pagas + minha_cota, 2)

            itens.append(
                schemas.ItemExtratoMembro(
                    despesa_id=despesa.id,
                    descricao=despesa.descricao,
                    dia_compra=despesa.dia_compra,
                    dia_vencimento=despesa.dia_vencimento,
                    valor_total_despesa=despesa.valor_total,
                    pagador_id=despesa.pagador_id,
                    pagador_nome=pagador_nome,
                    minha_cota=minha_cota,
                    percentual=percentual,
                    eu_paguei=eu_paguei,
                    saldo_na_despesa=saldo_item,
                )
            )

        saldo_liquido = round(total_pago_por_mim - total_minhas_cotas_pagas, 2)

        return schemas.ExtratoMembroGrupo(
            grupo_id=grupo.id,
            grupo_nome=grupo.nome,
            usuario_id=usuario.id,
            usuario_nome=usuario.nome,
            total_pago_por_mim=total_pago_por_mim,
            total_minhas_cotas_pagas=total_minhas_cotas_pagas,
            saldo_liquido_atual=saldo_liquido,
            itens=itens,
        )