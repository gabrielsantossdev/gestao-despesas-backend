const API_URL = window.location.port === "8000" ? "" : "http://127.0.0.1:8000";

let usuariosCache = [];
let gruposCache = [];

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
      (Array.isArray(data.detail) ? `${data.detail[0].loc.slice(-1)[0]}: ${data.detail[0].msg}` : data.detail) ||
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

// USUÁRIOS
async function carregarUsuarios() {
  try {
    usuariosCache = await apiFetch("/usuarios/");
    const tbody = document.getElementById("lista-usuarios");
    tbody.innerHTML = usuariosCache.length
      ? usuariosCache
          .map(
            (u) => `<tr>
              <td>#${u.id}</td>
              <td><strong>${u.nome}</strong></td>
              <td>${u.email}</td>
              <td><code>${u.chave_pix}</code></td>
            </tr>`
          )
          .join("")
      : `<tr><td colspan="4">Nenhum usuário cadastrado.</td></tr>`;

    const selMembro = document.getElementById("m-usuario-id");
    selMembro.innerHTML = usuariosCache
      .map((u) => `<option value="${u.id}">${u.nome} (${u.email})</option>`)
      .join("");
  } catch (e) {
    mostrarAlerta(e.message, "erro");
  }
}

document.getElementById("form-usuario").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await apiFetch("/usuarios/", {
      method: "POST",
      body: JSON.stringify({
        nome: document.getElementById("u-nome").value,
        telefone: document.getElementById("u-telefone").value,
        cpf: document.getElementById("u-cpf").value,
        email: document.getElementById("u-email").value,
        senha: document.getElementById("u-senha").value,
        chave_pix: document.getElementById("u-pix").value,
      }),
    });
    e.target.reset();
    mostrarAlerta("Usuário cadastrado com sucesso!");
    await carregarUsuarios();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
});

// GRUPOS E MEMBROS
async function carregarGrupos() {
  try {
    gruposCache = await apiFetch("/grupos/");
    const lista = document.getElementById("lista-grupos");
    lista.innerHTML = gruposCache.length
      ? gruposCache
          .map(
            (g) => `<div class="item-box">
              <div class="item-top">
                <strong>#${g.id} — ${g.nome}</strong>
                <span class="badge">${g.membros.length} membro(s)</span>
              </div>
              <p style="margin: 8px 0 0; font-size: 0.88rem; color: #475569;">
                Integrantes: ${g.membros.length ? g.membros.map((m) => m.nome).join(", ") : "Nenhum membro vinculado"}
              </p>
            </div>`
          )
          .join("")
      : `<p>Nenhum grupo criado ainda.</p>`;

    const options = gruposCache.map((g) => `<option value="${g.id}">${g.nome}</option>`).join("");
    document.getElementById("m-grupo-id").innerHTML = options;
    document.getElementById("d-grupo-ativo").innerHTML = options;

    if (typeof atualizarPainelDespesas === "function") {
      await atualizarPainelDespesas();
    }
  } catch (e) {
    mostrarAlerta(e.message, "erro");
  }
}

document.getElementById("form-grupo").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await apiFetch("/grupos/", {
      method: "POST",
      body: JSON.stringify({ nome: document.getElementById("g-nome").value }),
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
  try {
    await apiFetch(`/grupos/${grupoId}/membros`, {
      method: "POST",
      body: JSON.stringify({ usuario_id: usuarioId }),
    });
    mostrarAlerta("Membro adicionado ao grupo!");
    await carregarGrupos();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
});

window.addEventListener("DOMContentLoaded", async () => {
  await carregarUsuarios();
  await carregarGrupos();
});

// DESPESAS E RESUMO FINANCEIRO
function getGrupoAtivoObj() {
  const id = Number(document.getElementById("d-grupo-ativo").value);
  return gruposCache.find((g) => g.id === id) || null;
}

function renderizarCamposDivisao() {
  const tipo = document.getElementById("d-tipo").value;
  const box = document.getElementById("box-divisao-custom");
  const grupo = getGrupoAtivoObj();

  if (tipo === "IGUAL" || !grupo || !grupo.membros.length) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }

  const labelUnidade = tipo === "EXATA" ? "Valor (R$)" : "Percentual (%)";
  box.classList.remove("hidden");
  box.innerHTML =
    `<p style="margin:0 0 8px; font-size:0.85rem;"><strong>Informe o ${labelUnidade} por membro:</strong></p>` +
    grupo.membros
      .map(
        (m) => `<div class="custom-row">
          <span>${m.nome}</span>
          <input type="number" step="0.01" min="0" class="input-divisao" data-user-id="${m.id}" placeholder="0.00" required />
        </div>`
      )
      .join("");
}

async function atualizarPainelDespesas() {
  const grupo = getGrupoAtivoObj();
  const selPagador = document.getElementById("d-pagador");

  if (!grupo) {
    selPagador.innerHTML = "";
    document.getElementById("lista-despesas").innerHTML = "<p>Crie um grupo primeiro.</p>";
    return;
  }

  selPagador.innerHTML = grupo.membros
    .map((m) => `<option value="${m.id}">${m.nome}</option>`)
    .join("");
  renderizarCamposDivisao();

  try {
    const [despesas, resumo] = await Promise.all([
      apiFetch(`/despesas/grupo/${grupo.id}`),
      apiFetch(`/grupos/${grupo.id}/resumo`),
    ]);

    document.getElementById("total-grupo-badge").textContent =
      `Total: R$ ${resumo.total_despesas_grupo.toFixed(2)}`;

    document.getElementById("resumo-saldos").innerHTML = resumo.saldos
      .map((s) => {
        const cls = s.saldo_liquido > 0 ? "saldo-pos" : s.saldo_liquido < 0 ? "saldo-neg" : "";
        const sinal = s.saldo_liquido > 0 ? "+" : "";
        return `<div class="item-box item-top">
          <span><strong>${s.nome}</strong> (Pagou R$ ${s.total_pago.toFixed(2)} | Deve R$ ${s.total_devido.toFixed(2)})</span>
          <span class="${cls}">${sinal}R$ ${s.saldo_liquido.toFixed(2)}</span>
        </div>`;
      })
      .join("");

    document.getElementById("resumo-acertos").innerHTML = resumo.acertos_simplificados.length
      ? resumo.acertos_simplificados
          .map(
            (a) => `<div class="acerto-card">
              <div><strong>${a.devedor_nome}</strong> deve transferir <strong>R$ ${a.valor.toFixed(2)}</strong> para <strong>${a.credor_nome}</strong></div>
              <div class="pix-row">
                <span>Chave PIX: <code>${a.credor_chave_pix}</code></span>
                <button type="button" class="btn-outline" onclick="navigator.clipboard.writeText('${a.credor_chave_pix}'); mostrarAlerta('Chave PIX copiada!')">Copiar PIX</button>
              </div>
            </div>`
          )
          .join("")
      : `<p style="color:#64748b; font-size:0.9rem;">Nenhuma transferência pendente no grupo.</p>`;

    document.getElementById("lista-despesas").innerHTML = despesas.length
      ? despesas
          .map((d) => {
            const pagador = grupo.membros.find((m) => m.id === d.pagador_id);
            return `<div class="item-box item-top">
              <div>
                <strong>${d.descricao}</strong> — R$ ${d.valor_total.toFixed(2)}
                <div style="font-size:0.82rem; color:#64748b;">Pago por: ${pagador ? pagador.nome : "#" + d.pagador_id} | Data: ${d.dia_compra}</div>
              </div>
              <button type="button" class="btn-danger" onclick="excluirDespesa(${d.id})">Excluir</button>
            </div>`;
          })
          .join("")
      : `<p style="color:#64748b; font-size:0.9rem;">Nenhuma despesa lançada neste grupo.</p>`;
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
}

async function excluirDespesa(id) {
  try {
    await apiFetch(`/despesas/${id}`, { method: "DELETE" });
    mostrarAlerta("Despesa excluída!");
    await atualizarPainelDespesas();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
}

document.getElementById("d-grupo-ativo").addEventListener("change", atualizarPainelDespesas);
document.getElementById("d-tipo").addEventListener("change", renderizarCamposDivisao);

document.getElementById("form-despesa").addEventListener("submit", async (e) => {
  e.preventDefault();
  const grupo = getGrupoAtivoObj();
  if (!grupo) return;

  const tipo = document.getElementById("d-tipo").value;
  let divisoes = null;

  if (tipo !== "IGUAL") {
    divisoes = Array.from(document.querySelectorAll(".input-divisao")).map((inp) => ({
      usuario_id: Number(inp.dataset.userId),
      [tipo === "EXATA" ? "valor_devido" : "percentual"]: Number(inp.value),
    }));
  }

  const diaCompra = document.getElementById("d-compra").value || null;

  try {
    await apiFetch("/despesas/", {
      method: "POST",
      body: JSON.stringify({
        descricao: document.getElementById("d-descricao").value,
        valor_total: Number(document.getElementById("d-valor").value),
        dia_compra: diaCompra,
        grupo_id: grupo.id,
        pagador_id: Number(document.getElementById("d-pagador").value),
        tipo_divisao: tipo,
        divisoes,
      }),
    });
    e.target.reset();
    mostrarAlerta("Despesa registrada e saldos recalculados!");
    await atualizarPainelDespesas();
  } catch (err) {
    mostrarAlerta(err.message, "erro");
  }
});