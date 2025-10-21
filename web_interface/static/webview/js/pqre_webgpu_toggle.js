const params = new URLSearchParams(window.location.search);
const STORAGE_KEY = "pqre_webgpu_pref";

const PQREWebGPU = {
  available: typeof navigator !== "undefined" && !!navigator.gpu,
  enabled: false,
  reason: "",
};

function setBadgeState(state) {
  const badge = document.getElementById("pqre-webgpu-support");
  if (!badge) {
    return;
  }
  badge.classList.remove("ready", "review", "hold");
  if (state === "ready") {
    badge.classList.add("ready");
    badge.textContent = "WebGPU";
  } else if (state === "review") {
    badge.classList.add("review");
    badge.textContent = "Preview";
  } else {
    badge.classList.add("hold");
    badge.textContent = "WebGL";
  }
}

function updateUi() {
  const status = document.getElementById("pqre-webgpu-status");
  const button = document.getElementById("pqre-webgpu-toggle");
  if (!status || !button) {
    return;
  }

  if (!PQREWebGPU.available) {
    setBadgeState("hold");
    status.textContent = "This browser does not expose WebGPU; staying on the safe WebGL pipeline.";
    button.disabled = true;
    button.textContent = "WebGPU unavailable";
    return;
  }

  if (PQREWebGPU.enabled) {
    setBadgeState("ready");
    status.textContent = "WebGPU acceleration active — PQRE visuals render in high fidelity.";
    button.textContent = "Disable WebGPU";
    button.disabled = false;
  } else {
    setBadgeState("review");
    status.textContent = "Using the baseline WebGL renderer. Enable WebGPU for experimental PQRE visuals.";
    button.textContent = "Enable WebGPU";
    button.disabled = false;
  }
}

function persistPreference() {
  try {
    localStorage.setItem(STORAGE_KEY, PQREWebGPU.enabled ? "on" : "off");
  } catch (err) {
    console.debug("webgpu pref skip", err);
  }
}

function dispatchChange() {
  window.dispatchEvent(
    new CustomEvent("pqre:webgpu-change", {
      detail: {
        enabled: PQREWebGPU.enabled,
        available: PQREWebGPU.available,
      },
    })
  );
}

function applyDataAttribute() {
  document.documentElement.dataset.pqreWebgpu = PQREWebGPU.enabled ? "on" : "off";
}

function togglePreference() {
  PQREWebGPU.enabled = !PQREWebGPU.enabled;
  persistPreference();
  applyDataAttribute();
  updateUi();
  dispatchChange();
}

function restorePreference() {
  if (!PQREWebGPU.available) {
    PQREWebGPU.enabled = false;
    return;
  }
  const query = params.get("webgpu");
  if (query && query !== "0" && query !== "false") {
    PQREWebGPU.enabled = true;
    return;
  }
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "on") {
      PQREWebGPU.enabled = true;
    }
  } catch (err) {
    console.debug("webgpu pref load skip", err);
  }
}

function init() {
  const card = document.getElementById("pqre-card");
  if (!card) {
    return;
  }
  restorePreference();
  applyDataAttribute();
  updateUi();
  const button = document.getElementById("pqre-webgpu-toggle");
  if (button) {
    button.addEventListener("click", togglePreference);
  }
}

window.addEventListener("DOMContentLoaded", init, { once: true });
window.PQREWebGPU = PQREWebGPU;
