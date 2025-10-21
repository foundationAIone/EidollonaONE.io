const params = new URLSearchParams(window.location.search);
const avatarId = params.get("id") || "fancomp";
const apiBase = params.get("base") || "";
const token = params.get("token") || "dev-token";
const vrmUrl = params.get("vrmUrl") || params.get("vrm") || "";

function joinUrl(...parts) {
  const filtered = parts.filter((part) => part !== undefined && part !== null && part !== "");
  return filtered
    .map((segment, index) => {
      const value = String(segment);
      if (index === 0) {
        return value.replace(/\/$/, "");
      }
      return value.replace(/^\/+/, "").replace(/\/+$/, "");
    })
    .join("/");
}

const baseUrl = joinUrl(apiBase, "v1", "avatar", avatarId);

const dashboardEl = document.getElementById("dashboard");
const transcriptEl = document.getElementById("transcript");
const titleEl = document.getElementById("avatar-title");
const actionSelect = document.getElementById("action-select");
const uploadModal = document.getElementById("modal-upload");
const requestModal = document.getElementById("modal-request");
const statusEl = document.getElementById("avatar-status");

const FALLBACK_PERSONAS = {
  fancomp: {
    name: "FanComp Foundation",
    tone: "supportive, clear, creator-centric",
  },
  serveit: {
    name: "Serve-it",
    tone: "practical, action-oriented",
  },
};

function setTranscript(text) {
  transcriptEl.textContent = text;
}

function renderDashboard(data) {
  dashboardEl.innerHTML = "";
  if (!data || !data.widgets) {
    return;
  }
  const { kpis = [], tables = [] } = data.widgets;
  if (kpis.length) {
    const kpiContainer = document.createElement("div");
    kpiContainer.className = "card";
    kpiContainer.innerHTML = `<h3>KPIs</h3>`;
    kpis.forEach((item) => {
      const row = document.createElement("div");
      row.innerHTML = `<div class="kpi-value">${item.value ?? "--"}</div><div>${item.name}</div>`;
      kpiContainer.appendChild(row);
    });
    dashboardEl.appendChild(kpiContainer);
  }
  tables.forEach((table) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h3>${table.title || "Table"}</h3>`;
    const list = document.createElement("div");
    (table.rows || []).forEach((row) => {
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(row, null, 2);
      list.appendChild(pre);
    });
    card.appendChild(list);
    dashboardEl.appendChild(card);
  });
}

async function fetchJSON(url, options = {}) {
  const divider = url.includes("?") ? "&" : "?";
  const response = await fetch(`${url}${divider}token=${encodeURIComponent(token)}`, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }
  return response.json();
}

async function fetchDashboard() {
  try {
    const data = await fetchJSON(`${baseUrl}/dashboard`);
    renderDashboard(data.dashboard || data);
    if (statusEl) {
      statusEl.textContent = "Dashboard refreshed";
    }
  } catch (err) {
    setTranscript(`Dashboard error: ${err.message}`);
  }
}

async function postIntent(intent, args = {}) {
  const payload = {
    session_id: params.get("session") || `session_${Date.now()}`,
    intent,
    args,
  };
  const response = await fetchJSON(`${baseUrl}/intent`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (response.widgets) {
    renderDashboard(response.widgets);
  }
  if (response.dashboard) {
    renderDashboard(response.dashboard);
  }
  if (response.speech) {
    setTranscript(response.speech);
  } else {
    setTranscript(JSON.stringify(response, null, 2));
  }
  return response;
}

function openModal(el) {
  if (el) {
    el.classList.add("active");
  }
}

function closeModal(el) {
  if (el) {
    el.classList.remove("active");
  }
}

function wireModalControls() {
  document.querySelectorAll("[data-close]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modal = document.getElementById(btn.getAttribute("data-close"));
      closeModal(modal);
    });
  });
  document.querySelectorAll("[data-submit='upload']").forEach((btn) => {
    btn.addEventListener("click", async () => {
      closeModal(uploadModal);
      await postIntent("upload_ip", {
        artist_name: document.getElementById("upload-artist").value || "Guest",
        title: document.getElementById("upload-title").value || "Untitled",
        price_cents: parseInt(document.getElementById("upload-price").value || "0", 10),
        metadata: {
          notes: document.getElementById("upload-notes").value,
        },
      });
      fetchDashboard();
    });
  });
  document.querySelectorAll("[data-submit='request']").forEach((btn) => {
    btn.addEventListener("click", async () => {
      closeModal(requestModal);
      await postIntent("quote_task", {
        service_type: document.getElementById("request-category").value || "general",
        description: document.getElementById("request-description").value || "",
      });
      fetchDashboard();
    });
  });
}

function wireControls() {
  document.querySelectorAll("button[data-action]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const action = btn.getAttribute("data-action");
      if (action === "explain") {
        await postIntent("explain_state");
      } else if (action === "dashboard") {
        fetchDashboard();
      } else if (action === "upload" && avatarId === "fancomp") {
        openModal(uploadModal);
      } else if (action === "request" && avatarId === "serveit") {
        openModal(requestModal);
      } else if (action === "run-selected") {
        const selected = actionSelect.value;
        if (!selected) {
          setTranscript("Choose an action from the menu.");
          return;
        }
        const args = {};
        if (selected === "join_pool") {
          args.content_id = prompt("Content ID") || "";
          args.amount_cents = parseInt(prompt("Amount (cents)") || "100", 10);
        }
        await postIntent(selected, args);
      }
    });
  });
}

async function loadPersona() {
  const personaCandidates = [
    `../../${avatarId}/persona.json`,
    `/avatars/${avatarId}/persona.json`,
  ];
  let persona = FALLBACK_PERSONAS[avatarId] || { name: avatarId };
  for (const candidate of personaCandidates) {
    try {
      const res = await fetch(candidate);
      if (res.ok) {
        persona = await res.json();
        break;
      }
    } catch (err) {
      // ignore, fallback below
    }
  }
  if (titleEl) {
    titleEl.textContent = `${persona.name} Avatar`;
  }
  if (statusEl) {
    statusEl.textContent = `Tone: ${persona.tone || "n/a"}`;
  }
}

function initVRM() {
  if (!vrmUrl) {
    return;
  }
  window.dispatchEvent(
    new CustomEvent("hud:vrm-load", {
      detail: {
        url: vrmUrl,
      },
    })
  );
}

async function bootstrap() {
  await loadPersona();
  wireControls();
  wireModalControls();
  fetchDashboard();
  postIntent("explain_state");
  initVRM();
}

bootstrap();
