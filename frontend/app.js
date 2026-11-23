const API_URL = window.location.port === "8000" ? "" : "http://127.0.0.1:8000";
const STORAGE_RESP_PIX = "rateio_facil_resp_pix";

let usuarioLogado = null;
let meusAmigosCache = [];
let gruposCache = [];

function getUsuarioAtivoId() {
  return usuarioLogado ? usuarioLogado.id : null;
}

function getResponsaveisPixMap() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_RESP_PIX) || "{}");
  } catch {
    return {};
  }
}

function salvarResponsavelPix(despesaId, usuarioId) {
  const mapa = getResponsaveisPixMap();
  if (usuarioId) {
    mapa[String(despesaId)] = Number(usuarioId);
  } else {
    delete mapa[String(despesaId)];
  }
  localStorage.setItem(STORAGE_RESP_PIX, JSON.stringify(mapa));
}

function isLancamentoAcertoPix(descricao) {
  return typeof descricao === "string" && descricao.startsWith("Acerto PIX:");
}

function formatarMoeda(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function formatarDataBR(isoDate) {
  if (!isoDate) return "";
  const [ano, mes, dia] = isoDate.split("-");
  return dia && mes && ano ? `${dia}/${mes}/${ano}` : isoDate;
}

function definirDataHoje() {
  const campoData = document.getElementById("d-compra");
  if (!campoData) return;
  const hoje = new Date();
  const offset = hoje.getTimezoneOffset();
  const local = new Date(hoje.getTime() - offset * 60000);
  campoData.value = local.toISOString().split("T")[0];
}

function mostrarAlerta(msg, tipo = "ok") {
  const el = document.getElementById("alerta");
  el.textContent = msg;
  el.className = `alerta ${tipo}`;
  setTimeout(() => el.classList.add("hidden"), 4500);
}

async function apiFetch(path, options = {}) {
  const resp = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (resp.status === 204) return null;
  const data = await resp.json();
  if (!resp.ok) {
    const detalhe =
      data.detalhe ||
      (Array.isArray(data.detail)
        ? `${data.detail[0].loc.slice(-1)[0]}: ${data.detail[0].msg}`
        : data.detail) ||
      "Erro ao processar requisição.";
    throw new Error(detalhe);
  }
  return data;
}

// Alternância de abas
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

// CONTA LOGADA (GABRIEL SANTOS)
async function inicializarContaLogada() {
  const usuarios = await apiFetch("/usuarios/");
  usuarioLogado =
    usuarios.find((u) => u.email === "gabriel@rateiofacil.com") || usuarios[0] || null;

  if (usuarioLogado) {
    document.getElementById("usuario-logado-nome").textContent = usuarioLogado.nome;
  }
}

// ABA 1: AMIGOS (BUSCA E ADIÇÃO POR E-MAIL)
async function carregarAmigos() {
  const uid = getUsuarioAtivoId();
  if (!uid) return;

  try {
    meusAmigosCache = await apiFetch(`/usuarios/${uid}/amigos`);
    const tbody = document.getElementById("lista-amigos");
    tbody.innerHTML = meusAmigosCache.length
      ? meusAmigosCache
          .map(
            (a) => `<tr>
              <td><strong>${a.nome}</strong></td>
              <td>${a.email}</td>
              <td><code>${a.chave_pix}</code></td>
              <td><button type="button" class="btn-danger" onclick="removerAmigo(${a.id})">Remover</button></td>
            </tr>`
          )
          .join("")
      : `<tr><td colspan="4">Você ainda não adicionou amigos.</td></tr>`;

    atualizarSelectAmigosGrupo();
  } catch (e) {
    mostrarAlerta(e.message, "erro");
  }
}

async function removerAmigo(amigoId) {
  const uid = getUsuarioAtivoId();
  try {
    await apiFetch(`/usuarios/${uid}/amigos/${amigoId}`, { method: "DELETE" });
    mostrarAlerta("Amigo removido da lista.");
    await carregarAmigos();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
}

document.getElementById("form-amigo-email").addEventListener("submit", async (e) => {
  e.preventDefault();
  const uid = getUsuarioAtivoId();
  const email = document.getElementById("amigo-email-input").value.trim();
  try {
    const amigo = await apiFetch(`/usuarios/${uid}/amigos`, {
      method: "POST",
      body: JSON.stringify({ email }),
    });
    e.target.reset();
    mostrarAlerta(`${amigo.nome} foi adicionado à sua lista de amigos!`);
    await carregarAmigos();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
});

// ABA 2: GRUPOS E MEMBROS
function atualizarSelectAmigosGrupo() {
  const grupoId = Number(document.getElementById("m-grupo-id").value);
  const grupo = gruposCache.find((g) => g.id === grupoId);
  const membrosIds = new Set(grupo ? grupo.membros.map((m) => m.id) : []);

  const amigosElegiveis = meusAmigosCache.filter((a) => !membrosIds.has(a.id));
  const selMembro = document.getElementById("m-usuario-id");

  selMembro.innerHTML = amigosElegiveis.length
    ? amigosElegiveis
        .map((a) => `<option value="${a.id}">${a.nome} (${a.email})</option>`)
        .join("")
    : `<option value="">Todos os seus amigos já estão neste grupo</option>`;
}

async function carregarGrupos() {
  try {
    gruposCache = await apiFetch("/grupos/");
    const lista = document.getElementById("lista-grupos");
    lista.innerHTML = gruposCache.length
      ? gruposCache
          .map(
            (g) => `<div class="item-box">
              <div class="item-top">
                <div>
                  <strong>${g.nome}</strong>
                  <span class="badge" style="margin-left:6px;">${g.membros.length} integrante(s)</span>
                </div>
                <button type="button" class="btn-danger" onclick="excluirGrupo(${g.id})">Excluir Grupo</button>
              </div>
              <div class="member-chips">
                ${
                  g.membros.length
                    ? g.membros
                        .map(
                          (m) => `<span class="member-chip">
                            ${m.nome}
                            <button type="button" class="chip-remove" title="Remover do grupo" onclick="removerMembroGrupo(${g.id}, ${m.id})">&times;</button>
                          </span>`
                        )
                        .join("")
                    : `<span style="font-size:0.85rem; color:#64748b;">Nenhum integrante no grupo.</span>`
                }
              </div>
            </div>`
          )
          .join("")
      : `<p style="color:#64748b; font-size:0.9rem;">Nenhum grupo criado ainda.</p>`;

    const prevGrupoMembro = document.getElementById("m-grupo-id").value;
    const prevGrupoAtivo = document.getElementById("d-grupo-ativo").value;

    const options = gruposCache.map((g) => `<option value="${g.id}">${g.nome}</option>`).join("");
    document.getElementById("m-grupo-id").innerHTML = options;
    document.getElementById("d-grupo-ativo").innerHTML = options;

    if (prevGrupoMembro && gruposCache.some((g) => String(g.id) === prevGrupoMembro)) {
      document.getElementById("m-grupo-id").value = prevGrupoMembro;
    }
    if (prevGrupoAtivo && gruposCache.some((g) => String(g.id) === prevGrupoAtivo)) {
      document.getElementById("d-grupo-ativo").value = prevGrupoAtivo;
    }

    atualizarSelectAmigosGrupo();
    await atualizarPainelDespesas();
  } catch (e) {
    mostrarAlerta(e.message, "erro");
  }
}

async function removerMembroGrupo(grupoId, usuarioId) {
  try {
    await apiFetch(`/grupos/${grupoId}/membros/${usuarioId}`, { method: "DELETE" });
    mostrarAlerta("Integrante removido do grupo.");
    await carregarGrupos();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
}

async function excluirGrupo(grupoId) {
  try {
    await apiFetch(`/grupos/${grupoId}`, { method: "DELETE" });
    mostrarAlerta("Grupo excluído.");
    await carregarGrupos();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
}

document.getElementById("m-grupo-id").addEventListener("change", atualizarSelectAmigosGrupo);

document.getElementById("form-grupo").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await apiFetch("/grupos/", {
      method: "POST",
      body: JSON.stringify({
        nome: document.getElementById("g-nome").value,
        criador_id: getUsuarioAtivoId(),
      }),
    });
    e.target.reset();
    mostrarAlerta("Grupo criado com sucesso!");
    await carregarGrupos();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
});

document.getElementById("form-membro").addEventListener("submit", async (e) => {
  e.preventDefault();
  const grupoId = document.getElementById("m-grupo-id").value;
  const usuarioId = Number(document.getElementById("m-usuario-id").value);
  if (!usuarioId) {
    mostrarAlerta("Adicione amigos por e-mail na Aba 1 antes de incluí-los no grupo.", "erro");
    return;
  }
  try {
    await apiFetch(`/grupos/${grupoId}/membros`, {
      method: "POST",
      body: JSON.stringify({
        usuario_id: usuarioId,
        solicitante_id: getUsuarioAtivoId(),
      }),
    });
    mostrarAlerta("Amigo adicionado ao grupo!");
    await carregarGrupos();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
});

// ABA 3: DESPESAS, PENDÊNCIAS, EXTRATO INDIVIDUAL E ACERTO PIX
function getGrupoAtivoObj() {
  const id = Number(document.getElementById("d-grupo-ativo").value);
  return gruposCache.find((g) => g.id === id) || null;
}

function alternarVisibilidadePagador() {
  const statusVal = document.getElementById("d-status").value;
  const wrapPagador = document.getElementById("wrap-pagador");
  const wrapRespPix = document.getElementById("wrap-responsavel-pix");

  if (statusVal === "PENDENTE") {
    wrapPagador.classList.add("hidden");
    wrapRespPix.classList.remove("hidden");
  } else {
    wrapPagador.classList.remove("hidden");
    wrapRespPix.classList.add("hidden");
  }
}

function renderizarCamposDivisao() {
  const tipo = document.getElementById("d-tipo").value;
  const box = document.getElementById("box-divisao-custom");
  const grupo = getGrupoAtivoObj();

  if (!grupo || !grupo.membros.length) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }

  box.classList.remove("hidden");

  if (tipo === "IGUAL") {
    box.innerHTML =
      `<p style="margin:0 0 8px; font-size:0.85rem;"><strong>Quem participou desta despesa?</strong></p>` +
      `<div class="check-grid">` +
      grupo.membros
        .map(
          (m) => `<label class="check-item">
            <input type="checkbox" class="check-participante" value="${m.id}" checked />
            <span>${m.nome}</span>
          </label>`
        )
        .join("") +
      `</div>`;
    return;
  }

  const labelUnidade = tipo === "EXATA" ? "Valor (R$)" : "Percentual (%)";
  box.innerHTML =
    `<p style="margin:0 0 8px; font-size:0.85rem;"><strong>Informe o ${labelUnidade} por membro:</strong></p>` +
    grupo.membros
      .map(
        (m) => `<div class="custom-row">
          <span>${m.nome}</span>
          <input type="number" step="0.01" min="0" class="input-divisao" data-user-id="${m.id}" placeholder="0,00" required />
        </div>`
      )
      .join("");
}

function formatarStatusSaldo(valor) {
  if (valor > 0.009) {
    return { cls: "saldo-pos", texto: `Recebe ${formatarMoeda(valor)}` };
  }
  if (valor < -0.009) {
    return { cls: "saldo-neg", texto: `Deve ${formatarMoeda(Math.abs(valor))}` };
  }
  return { cls: "", texto: "Quitado (R$ 0,00)" };
}

function copiarChavePix(btn) {
  const chave = btn.dataset.pix || "";
  navigator.clipboard.writeText(chave);
  mostrarAlerta("Chave PIX copiada!");
}

async function registrarPagamentoPix(devedorId, credorId, valor) {
  const grupo = getGrupoAtivoObj();
  if (!grupo) return;

  const devedor = grupo.membros.find((m) => m.id === devedorId);
  const credor = grupo.membros.find((m) => m.id === credorId);
  const descricao = `Acerto PIX: ${devedor ? devedor.nome : "#" + devedorId} → ${credor ? credor.nome : "#" + credorId}`;

  try {
    await apiFetch("/despesas/", {
      method: "POST",
      body: JSON.stringify({
        descricao,
        valor_total: Number(valor),
        status: "PAGA",
        grupo_id: grupo.id,
        pagador_id: devedorId,
        tipo_divisao: "EXATA",
        divisoes: [{ usuario_id: credorId, valor_devido: Number(valor) }],
      }),
    });
    mostrarAlerta("Pagamento via PIX registrado e saldos atualizados!");
    await atualizarPainelDespesas();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
}

async function atualizarPainelDespesas() {
  const grupo = getGrupoAtivoObj();
  const selPagador = document.getElementById("d-pagador");
  const selRespPix = document.getElementById("d-responsavel-pix");

  if (!grupo) {
    selPagador.innerHTML = "";
    selRespPix.innerHTML = "";
    document.getElementById("lista-despesas").innerHTML = "<p>Crie um grupo primeiro.</p>";
    document.getElementById("lista-pendentes").innerHTML = "";
    document.getElementById("lista-extrato-membro").innerHTML = "";
    return;
  }

  const optionsMembros = grupo.membros
    .map((m) => `<option value="${m.id}">${m.nome}</option>`)
    .join("");

  selPagador.innerHTML = optionsMembros;
  selRespPix.innerHTML = optionsMembros;

  if (usuarioLogado && grupo.membros.some((m) => m.id === usuarioLogado.id)) {
    selPagador.value = String(usuarioLogado.id);
    selRespPix.value = String(usuarioLogado.id);
  }
  renderizarCamposDivisao();

  try {
    const [despesas, resumo] = await Promise.all([
      apiFetch(`/despesas/grupo/${grupo.id}`),
      apiFetch(`/grupos/${grupo.id}/resumo`),
    ]);

    const pendentes = despesas.filter((d) => d.status === "PENDENTE");
    const pagas = despesas.filter((d) => d.status !== "PENDENTE");
    const despesasReaisPagas = pagas.filter((d) => !isLancamentoAcertoPix(d.descricao));
    const acertosPixPagos = pagas.filter((d) => isLancamentoAcertoPix(d.descricao));

    const totalRealPagoGrupo = despesasReaisPagas.reduce(
      (acc, d) => acc + Number(d.valor_total || 0),
      0
    );

    document.getElementById("total-grupo-badge").textContent =
      `Pago: ${formatarMoeda(totalRealPagoGrupo)}`;
    document.getElementById("total-pendente-badge").textContent =
      `Pendente: ${formatarMoeda(resumo.total_pendente_grupo)}`;

    // Saldos acumulados separando gasto real de acerto PIX
    document.getElementById("resumo-saldos").innerHTML = resumo.saldos
      .map((s) => {
        const status = formatarStatusSaldo(s.saldo_liquido);
        const pagoReal = despesasReaisPagas
          .filter((d) => d.pagador_id === s.usuario_id)
          .reduce((acc, d) => acc + Number(d.valor_total || 0), 0);

        const pixEnviado = acertosPixPagos
          .filter((d) => d.pagador_id === s.usuario_id)
          .reduce((acc, d) => acc + Number(d.valor_total || 0), 0);

        let pixRecebidoExato = 0;
        acertosPixPagos.forEach((d) => {
          if (Array.isArray(d.divisoes)) {
            d.divisoes.forEach((div) => {
              if (div.usuario_id === s.usuario_id) {
                pixRecebidoExato += Number(div.valor_devido || 0);
              }
            });
          }
        });

        const parteReal = Math.max(0, Number(s.total_devido) - pixRecebidoExato);

        let infoExtra = "";
        if (pixEnviado > 0.009) {
          infoExtra += ` • Quitou ${formatarMoeda(pixEnviado)} via PIX`;
        }
        if (pixRecebidoExato > 0.009) {
          infoExtra += ` • Recebeu ${formatarMoeda(pixRecebidoExato)} via PIX`;
        }

        return `<div class="item-box item-top">
          <div>
            <strong>${s.nome}</strong>
            <div style="font-size:0.82rem; color:#64748b;">
              Pagou ${formatarMoeda(pagoReal)} • Sua parte: ${formatarMoeda(parteReal)}${infoExtra}
            </div>
          </div>
          <span class="${status.cls}">${status.texto}</span>
        </div>`;
      })
      .join("");

    // Acertos PIX com botão de dar baixa
    document.getElementById("resumo-acertos").innerHTML = resumo.acertos_simplificados.length
      ? resumo.acertos_simplificados
          .map(
            (a) => `<div class="acerto-card">
              <div><strong>${a.devedor_nome}</strong> deve transferir <strong>${formatarMoeda(a.valor)}</strong> para <strong>${a.credor_nome}</strong></div>
              <div class="pix-row">
                <span>Chave PIX: <code>${a.credor_chave_pix}</code></span>
                <div class="pix-actions">
                  <button type="button" class="btn-outline" data-pix="${a.credor_chave_pix}" onclick="copiarChavePix(this)">Copiar PIX</button>
                  <button type="button" class="btn-success-sm" onclick="registrarPagamentoPix(${a.devedor_id}, ${a.credor_id}, ${a.valor})">Quitar PIX</button>
                </div>
              </div>
            </div>`
          )
          .join("")
      : `<p style="color:#64748b; font-size:0.9rem;">Tudo acertado! Nenhuma transferência pendente.</p>`;

    // Despesas PENDENTES
    const mapaRespPix = getResponsaveisPixMap();

    document.getElementById("lista-pendentes").innerHTML = pendentes.length
      ? pendentes
          .map((d) => {
            const respId = mapaRespPix[String(d.id)] || null;
            const respMembro =
              (respId && grupo.membros.find((m) => m.id === respId)) ||
              (usuarioLogado && grupo.membros.find((m) => m.id === usuarioLogado.id)) ||
              grupo.membros[0] ||
              null;

            const pagadorDefault = respMembro ? respMembro.id : grupo.membros[0]?.id;

            const opcoesMembros = grupo.membros
              .map(
                (m) =>
                  `<option value="${m.id}" ${m.id === pagadorDefault ? "selected" : ""}>${m.nome}</option>`
              )
              .join("");

            const blocoPixResponsavel = respMembro
              ? `<div class="pix-row" style="margin-top:8px;">
                  <span>Responsável pelo PIX: <strong>${respMembro.nome}</strong> • <code>${respMembro.chave_pix}</code></span>
                  <button type="button" class="btn-outline" data-pix="${respMembro.chave_pix}" onclick="copiarChavePix(this)">Copiar PIX</button>
                </div>`
              : "";

            return `<div class="item-box item-pendente">
              <div class="item-top">
                <div>
                  <strong>${d.descricao}</strong> — ${formatarMoeda(d.valor_total)}
                  <div style="font-size:0.82rem; color:#92400e;">Vencimento / Data: ${formatarDataBR(d.dia_compra)}</div>
                </div>
                <button type="button" class="btn-danger" onclick="excluirDespesa(${d.id}, false)">Excluir</button>
              </div>
              ${blocoPixResponsavel}
              <div class="pend-actions">
                <button type="button" class="btn-success-sm" onclick="quitarColetivamente(${d.id})">Quitada (Todos pagaram)</button>
                <div class="pend-reembolso-box">
                  <select id="pagador-pend-${d.id}" class="select-compact" title="Quem pagou a conta sozinho?">
                    ${opcoesMembros}
                  </select>
                  <button type="button" class="btn-warn" onclick="quitarDespesa(${d.id})">Pago por este membro</button>
                </div>
              </div>
            </div>`;
          })
          .join("")
      : `<p style="color:#64748b; font-size:0.9rem;">Nenhuma conta pendente de pagamento.</p>`;

    // Histórico apenas das despesas reais pagas
    document.getElementById("lista-despesas").innerHTML = despesasReaisPagas.length
      ? despesasReaisPagas
          .map((d) => {
            const pagador = grupo.membros.find((m) => m.id === d.pagador_id);
            return `<div class="item-box item-top">
              <div>
                <strong>${d.descricao}</strong> — ${formatarMoeda(d.valor_total)}
                <div style="font-size:0.82rem; color:#64748b;">
                  Pago por: ${pagador ? pagador.nome : "#" + d.pagador_id} • Data: ${formatarDataBR(d.dia_compra)}
                </div>
              </div>
              <button type="button" class="btn-danger" onclick="excluirDespesa(${d.id}, false)">Excluir</button>
            </div>`;
          })
          .join("")
      : `<p style="color:#64748b; font-size:0.9rem;">Nenhuma despesa paga registrada neste grupo.</p>`;

    // Card separado para os Acertos PIX já registrados
    const cardAcertosRealizados = document.getElementById("card-acertos-realizados");
    const listaAcertosRealizados = document.getElementById("lista-acertos-realizados");

    if (acertosPixPagos.length) {
      cardAcertosRealizados.classList.remove("hidden");
      listaAcertosRealizados.innerHTML = acertosPixPagos
        .map((d) => {
          const pagador = grupo.membros.find((m) => m.id === d.pagador_id);
          return `<div class="item-box item-acerto item-top">
            <div>
              <strong>${d.descricao}</strong> — ${formatarMoeda(d.valor_total)}
              <div style="font-size:0.82rem; color:#0369a1;">
                Transferido por: ${pagador ? pagador.nome : "#" + d.pagador_id} • Data: ${formatarDataBR(d.dia_compra)}
              </div>
            </div>
            <button type="button" class="btn-outline" onclick="excluirDespesa(${d.id}, true)">Desfazer</button>
          </div>`;
        })
        .join("");
    } else {
      cardAcertosRealizados.classList.add("hidden");
      listaAcertosRealizados.innerHTML = "";
    }

    await atualizarExtratoIndividual(grupo);
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
}

async function atualizarExtratoIndividual(grupo) {
  const badge = document.getElementById("extrato-usuario-badge");
  const cardsBox = document.getElementById("extrato-resumo-cards");
  const listaBox = document.getElementById("lista-extrato-membro");

  if (!usuarioLogado || !grupo.membros.some((m) => m.id === usuarioLogado.id)) {
    badge.textContent = "Fora do grupo";
    cardsBox.innerHTML = "";
    listaBox.innerHTML = `<p style="color:#64748b; font-size:0.88rem;">Você ainda não participa deste grupo.</p>`;
    return;
  }

  badge.textContent = usuarioLogado.nome;
  const extrato = await apiFetch(`/grupos/${grupo.id}/membros/${usuarioLogado.id}/extrato`);
  const saldoFinal = formatarStatusSaldo(extrato.saldo_liquido_atual);

  let pagoDespesasReais = 0;
  let parteGastosReais = 0;
  let pixRecebidos = 0;
  let pixEnviados = 0;

  extrato.itens.forEach((item) => {
    const isPix = isLancamentoAcertoPix(item.descricao);
    if (isPix) {
      if (item.eu_paguei) {
        pixEnviados += Number(item.valor_total_despesa || 0);
      } else {
        pixRecebidos += Number(item.valor_total_despesa || 0);
      }
    } else if (item.status !== "PENDENTE") {
      if (item.eu_paguei) {
        pagoDespesasReais += Number(item.valor_total_despesa || 0);
      }
      parteGastosReais += Number(item.minha_cota || 0);
    }
  });

  cardsBox.innerHTML = `
    <div class="mini-stat">
      <span>Total que Paguei</span>
      <strong>${formatarMoeda(pagoDespesasReais)}</strong>
    </div>
    <div class="mini-stat">
      <span>Minha Parte nos Gastos</span>
      <strong>${formatarMoeda(parteGastosReais)}</strong>
    </div>
    <div class="mini-stat">
      <span>Em Aberto (Pendentes)</span>
      <strong class="saldo-warn">${formatarMoeda(extrato.total_pendente_a_pagar)}</strong>
    </div>
  `;

  const resumoPixLinha =
    pixRecebidos > 0.009 || pixEnviados > 0.009
      ? `<div style="text-align:right; font-size:0.82rem; color:#0369a1; margin-top:6px;">
          ${pixRecebidos > 0.009 ? `Acertos recebidos via PIX: <strong>${formatarMoeda(pixRecebidos)}</strong>` : ""}
          ${pixRecebidos > 0.009 && pixEnviados > 0.009 ? " • " : ""}
          ${pixEnviados > 0.009 ? `Acertos pagos via PIX: <strong>${formatarMoeda(pixEnviados)}</strong>` : ""}
        </div>`
      : "";

  listaBox.innerHTML = extrato.itens.length
    ? extrato.itens
        .map((item) => {
          const isPendente = item.status === "PENDENTE";
          const isPix = isLancamentoAcertoPix(item.descricao);

          let detalhe = "";
          let statusItem = null;

          if (isPix) {
            if (item.eu_paguei) {
              detalhe = `Você transferiu ${formatarMoeda(item.valor_total_despesa)} via PIX para quitar sua dívida`;
              statusItem = {
                cls: "saldo-pix",
                texto: `Pago via PIX: ${formatarMoeda(item.valor_total_despesa)}`,
              };
            } else {
              detalhe = `Transferência recebida de <strong>${item.pagador_nome}</strong> para abater seu crédito`;
              statusItem = {
                cls: "saldo-pix",
                texto: `Recebido via PIX: ${formatarMoeda(item.valor_total_despesa)}`,
              };
            }
          } else if (isPendente) {
            detalhe = `Conta em aberto (total ${formatarMoeda(item.valor_total_despesa)}) • Sua parte: <strong>${formatarMoeda(item.minha_cota)}</strong>`;
            statusItem = {
              cls: "saldo-warn",
              texto: `A pagar: ${formatarMoeda(item.minha_cota)}`,
            };
          } else {
            detalhe = item.eu_paguei
              ? `Você pagou ${formatarMoeda(item.valor_total_despesa)} • Sua parte: ${formatarMoeda(item.minha_cota)}`
              : `Pago por ${item.pagador_nome} (${formatarMoeda(item.valor_total_despesa)}) • Sua parte: <strong>${formatarMoeda(item.minha_cota)}</strong>`;
            statusItem = formatarStatusSaldo(item.saldo_na_despesa);
          }

          return `<div class="item-box ${isPix ? "item-acerto" : ""} item-top">
            <div>
              <strong>${item.descricao}</strong> <span style="font-size:0.78rem; color:#64748b;">(${formatarDataBR(item.dia_compra)})</span>
              <div style="font-size:0.82rem; color:#475569;">${detalhe}</div>
            </div>
            <span class="${statusItem.cls}">${statusItem.texto}</span>
          </div>`;
        })
        .join("") +
      resumoPixLinha +
      `<div style="text-align:right; font-size:0.9rem; margin-top:4px;">
        Balanço final de <strong>${extrato.usuario_nome}</strong>: <span class="${saldoFinal.cls}">${saldoFinal.texto}</span>
      </div>`
    : `<p style="color:#64748b; font-size:0.88rem;">Nenhuma despesa vinculada a você neste grupo.</p>`;
}

// Quita a conta pendente sem gerar dívidas (todos juntaram e pagaram)
async function quitarColetivamente(despesaId) {
  try {
    await apiFetch(`/despesas/${despesaId}`, { method: "DELETE" });
    salvarResponsavelPix(despesaId, null);
    mostrarAlerta("Conta marcada como quitada! Nenhuma dívida foi gerada entre os membros.");
    await atualizarPainelDespesas();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
}

// Quita a conta pendente em nome de um único pagador (gera reembolso)
async function quitarDespesa(despesaId) {
  const sel = document.getElementById(`pagador-pend-${despesaId}`);
  const pagadorId = sel ? Number(sel.value) : null;
  if (!pagadorId) {
    mostrarAlerta("Selecione quem pagou a conta.", "erro");
    return;
  }
  try {
    await apiFetch(`/despesas/${despesaId}/pagar`, {
      method: "PATCH",
      body: JSON.stringify({ pagador_id: pagadorId }),
    });
    salvarResponsavelPix(despesaId, null);
    mostrarAlerta("Despesa marcada como paga e rateada para reembolso!");
    await atualizarPainelDespesas();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
}

async function excluirDespesa(id, isAcerto = false) {
  try {
    await apiFetch(`/despesas/${id}`, { method: "DELETE" });
    salvarResponsavelPix(id, null);

    if (!isAcerto) {
      const grupo = getGrupoAtivoObj();
      if (grupo) {
        const restantes = await apiFetch(`/despesas/grupo/${grupo.id}`);
        const despesasReaisPagas = restantes.filter(
          (d) => d.status !== "PENDENTE" && !isLancamentoAcertoPix(d.descricao)
        );
        const acertosOrfaos = restantes.filter((d) => isLancamentoAcertoPix(d.descricao));

        if (despesasReaisPagas.length === 0 && acertosOrfaos.length > 0) {
          await Promise.all(
            acertosOrfaos.map((a) => apiFetch(`/despesas/${a.id}`, { method: "DELETE" }))
          );
        }
      }
    }

    mostrarAlerta(
      isAcerto
        ? "Acerto PIX desfeito! A transferência voltou a ficar pendente."
        : "Despesa excluída!"
    );
    await atualizarPainelDespesas();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
}

document.getElementById("d-grupo-ativo").addEventListener("change", atualizarPainelDespesas);
document.getElementById("d-tipo").addEventListener("change", renderizarCamposDivisao);
document.getElementById("d-status").addEventListener("change", alternarVisibilidadePagador);

document.getElementById("form-despesa").addEventListener("submit", async (e) => {
  e.preventDefault();
  const grupo = getGrupoAtivoObj();
  if (!grupo) return;

  const statusVal = document.getElementById("d-status").value;
  const tipo = document.getElementById("d-tipo").value;
  let divisoes = null;

  if (tipo === "IGUAL") {
    const selecionados = Array.from(
      document.querySelectorAll(".check-participante:checked")
    ).map((cb) => Number(cb.value));

    if (!selecionados.length) {
      mostrarAlerta("Selecione pelo menos um participante para dividir a despesa.", "erro");
      return;
    }
    divisoes = selecionados.map((uid) => ({ usuario_id: uid }));
  } else {
    divisoes = Array.from(document.querySelectorAll(".input-divisao")).map((inp) => ({
      usuario_id: Number(inp.dataset.userId),
      [tipo === "EXATA" ? "valor_devido" : "percentual"]: Number(inp.value),
    }));
  }

  const diaCompra = document.getElementById("d-compra").value || null;
  const pagadorId =
    statusVal === "PAGA" ? Number(document.getElementById("d-pagador").value) : null;
  const responsavelPixId =
    statusVal === "PENDENTE" ? Number(document.getElementById("d-responsavel-pix").value) : null;

  try {
    const criada = await apiFetch("/despesas/", {
      method: "POST",
      body: JSON.stringify({
        descricao: document.getElementById("d-descricao").value,
        valor_total: Number(document.getElementById("d-valor").value),
        dia_compra: diaCompra,
        status: statusVal,
        grupo_id: grupo.id,
        pagador_id: pagadorId,
        tipo_divisao: tipo,
        divisoes,
      }),
    });

    if (statusVal === "PENDENTE" && criada && criada.id && responsavelPixId) {
      salvarResponsavelPix(criada.id, responsavelPixId);
    }

    e.target.reset();
    definirDataHoje();
    alternarVisibilidadePagador();
    renderizarCamposDivisao();
    mostrarAlerta(
      statusVal === "PENDENTE"
        ? "Conta pendente registrada!"
        : "Despesa paga registrada e saldos recalculados!"
    );
    await atualizarPainelDespesas();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
});

window.addEventListener("DOMContentLoaded", async () => {
  definirDataHoje();
  await inicializarContaLogada();
  await carregarAmigos();
  await carregarGrupos();
});