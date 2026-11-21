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