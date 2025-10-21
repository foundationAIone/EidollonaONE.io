import { VRMExpressionPresetName } from "https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@2.0.6/lib/three-vrm.module.js";

const CAP_STORAGE_KEY = "sereneVisemeCap";
const DEFAULT_VISEME_CAP = 0.35;
const SUM_LIMIT = 1.2;
const SOURCE_ID = "voice-lipsync";
const VISEME_ALIAS = {
  A: Array.from(new Set(["A", VRMExpressionPresetName?.A || "aa", "aa"])),
  I: Array.from(new Set(["I", VRMExpressionPresetName?.I || "ih", "ih"])),
  U: Array.from(new Set(["U", VRMExpressionPresetName?.U || "ou", "ou"])),
  E: Array.from(new Set(["E", VRMExpressionPresetName?.E || "ee", "ee"])),
  O: Array.from(new Set(["O", VRMExpressionPresetName?.O || "oh", "oh"])),
};
const CANONICAL_VISEMES = Object.keys(VISEME_ALIAS);

function clamp(value, min = 0, max = 1) {
  if (!Number.isFinite(value)) {
    return min;
  }
  if (value < min) {
    return min;
  }
  if (value > max) {
    return max;
  }
  return value;
}

function readStoredCap() {
  try {
    const stored = localStorage.getItem(CAP_STORAGE_KEY);
    if (stored !== null) {
      return clamp(Number.parseFloat(stored), 0, 0.65);
    }
  } catch (err) {
    console.debug("ExpressionRouter: cap storage read skipped", err);
  }
  return DEFAULT_VISEME_CAP;
}

function persistCap(value) {
  try {
    localStorage.setItem(CAP_STORAGE_KEY, value.toFixed(3));
  } catch (err) {
    console.debug("ExpressionRouter: cap storage write skipped", err);
  }
}

class SovereignExpressionRouter {
  constructor() {
    this.sources = new Map();
    this.visemeCap = readStoredCap();
    this.lastApplied = 0;
  }

  getVisemeCap() {
    return this.visemeCap;
  }

  setVisemeCap(value, { persist = true } = {}) {
    const clamped = clamp(value, 0, 0.65);
    this.visemeCap = clamped;
    if (persist) {
      persistCap(clamped);
    }
    this.apply();
    return clamped;
  }

  route(sourceId, weights) {
    if (!sourceId) {
      return false;
    }
    const sanitized = {};
    CANONICAL_VISEMES.forEach((canonical) => {
      const aliases = VISEME_ALIAS[canonical] || [];
      let value = 0;
      aliases.forEach((alias) => {
        if (weights && typeof weights[alias] === "number") {
          value = Math.max(value, weights[alias]);
        }
      });
      sanitized[canonical] = clamp(value, 0, 1);
    });
    this.sources.set(sourceId, sanitized);
    return this.apply();
  }

  clear(sourceId) {
    if (!sourceId) {
      return;
    }
    this.sources.delete(sourceId);
    this.apply();
  }

  clearAll() {
    this.sources.clear();
    this.apply();
  }

  apply() {
    const manager = window.HUDVRM?.currentVRM?.expressionManager;
    if (!manager) {
      return false;
    }
    const aggregated = {};
    CANONICAL_VISEMES.forEach((canonical) => {
      aggregated[canonical] = 0;
    });

    for (const weights of this.sources.values()) {
      CANONICAL_VISEMES.forEach((canonical) => {
        const value = weights[canonical] ?? 0;
        if (value > aggregated[canonical]) {
          aggregated[canonical] = value;
        }
      });
    }

    const cap = this.visemeCap;
    let sum = 0;
    CANONICAL_VISEMES.forEach((canonical) => {
      const clamped = clamp(aggregated[canonical], 0, cap);
      aggregated[canonical] = clamped;
      sum += clamped;
    });

    if (sum > SUM_LIMIT) {
      const scale = SUM_LIMIT / sum;
      CANONICAL_VISEMES.forEach((canonical) => {
        aggregated[canonical] *= scale;
      });
    }

    CANONICAL_VISEMES.forEach((canonical) => {
      const aliases = VISEME_ALIAS[canonical] || [];
      aliases.forEach((alias) => {
        if (!alias) {
          return;
        }
        try {
          manager.setValue(alias, aggregated[canonical]);
        } catch (err) {
          console.debug("ExpressionRouter: setValue fallback", err);
        }
      });
    });

    if (typeof manager.update === "function") {
      manager.update();
    }
    this.lastApplied = performance.now();
    return true;
  }
}

const routerInstance = (() => {
  if (window.ExpressionRouter) {
    return window.ExpressionRouter;
  }
  const instance = new SovereignExpressionRouter();
  window.ExpressionRouter = instance;
  return instance;
})();

class VoiceLipSyncController {
  constructor(router) {
    this.router = router;
    this.active = false;
    this.audioCtx = null;
    this.analyser = null;
    this.mediaStream = null;
    this.sourceNode = null;
    this.data = null;
    this.animationId = null;
    this.smoothed = 0;
    this.intensity = 0;
    this.noiseFloor = 0.015;
    this.gain = 4.2;
    this.lastReadyCheck = 0;
    this.serBalance = null;
  this.bound = false;
    this.ui = {
      start: null,
      stop: null,
      status: null,
      meter: null,
      capSlider: null,
      capValue: null,
      ser: null,
    };

    window.addEventListener("hud:ser-update", (event) => {
      if (event?.detail && typeof event.detail.balance === "number") {
        this.serBalance = event.detail.balance;
        this.renderSerHint();
      }
    });
    window.addEventListener("hud:vrm-ready", () => {
      if (this.active) {
        this.router.apply();
        this.updateStatus("Mic live — avatar ready");
      }
    });
    window.addEventListener("hud:vrm-error", (event) => {
      if (this.active) {
        const message = event?.detail?.message || "VRM error";
        this.updateStatus(`Mic live — ${message}`);
      }
    });
  }

  bindUi() {
    this.ui = {
      start: document.getElementById("lip-sync-start"),
      stop: document.getElementById("lip-sync-stop"),
      status: document.getElementById("lip-sync-status"),
      meter: document.getElementById("lip-sync-meter"),
      capSlider: document.getElementById("lip-sync-cap"),
      capValue: document.getElementById("lip-sync-cap-value"),
      ser: document.getElementById("lip-sync-ser"),
    };

    const capValue = this.router.getVisemeCap();
    if (this.ui.capSlider) {
      this.ui.capSlider.value = String(Math.round(capValue * 100));
    }
    this.renderCap(capValue);

    if (!this.bound) {
      if (this.ui.capSlider) {
        this.ui.capSlider.addEventListener("input", (event) => {
          const next = clamp(Number(event.target.value) / 100, 0, 0.65);
          this.router.setVisemeCap(next);
          this.renderCap(next);
        });
      }
      if (this.ui.start) {
        this.ui.start.addEventListener("click", () => {
          void this.start();
        });
      }
      if (this.ui.stop) {
        this.ui.stop.addEventListener("click", () => {
          this.stop();
        });
        this.ui.stop.disabled = true;
      }
      this.bound = true;
    }
    this.renderSerHint();
    this.updateStatus("Mic idle");
  }

  renderCap(value) {
    if (this.ui.capSlider && document.activeElement !== this.ui.capSlider) {
      this.ui.capSlider.value = String(Math.round(value * 100));
    }
    if (this.ui.capValue) {
      this.ui.capValue.textContent = value.toFixed(2);
    }
  }

  renderSerHint() {
    if (!this.ui.ser) {
      return;
    }
    if (this.serBalance === null || Number.isNaN(this.serBalance)) {
      this.ui.ser.textContent = "SER ledger: —";
      return;
    }
    this.ui.ser.textContent = `SER ledger: ${this.serBalance.toFixed(2)} SER`;
  }

  updateStatus(message) {
    if (this.ui.status) {
      this.ui.status.textContent = message;
    }
  }

  updateMeter(value) {
    if (!this.ui.meter) {
      return;
    }
    const percent = clamp(value, 0, 1) * 100;
    this.ui.meter.style.setProperty("--lip-meter-fill", `${percent.toFixed(1)}%`);
  }

  async start() {
    if (this.active) {
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      this.updateStatus("Mic unavailable in this browser");
      return;
    }

    try {
      this.updateStatus("Requesting microphone…");
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: false,
        },
        video: false,
      });
      this.mediaStream = stream;
      try {
        await this.bootstrapAudio();
      } catch (err) {
        this.cleanupStream();
        throw err;
      }
      this.active = true;
      if (window.HUDVRM?.currentVRM?.expressionManager) {
        this.updateStatus("Mic live — avatar ready");
      } else {
        this.updateStatus("Mic live — awaiting avatar");
      }
      if (this.ui.start) {
        this.ui.start.disabled = true;
      }
      if (this.ui.stop) {
        this.ui.stop.disabled = false;
      }
      this.tick();
    } catch (err) {
      console.warn("VoiceLipSync: microphone start failed", err);
      this.updateStatus(`Mic error: ${err.message || err}`);
      this.cleanupStream();
      if (this.ui.start) {
        this.ui.start.disabled = false;
      }
    }
  }

  async bootstrapAudio() {
    if (!this.mediaStream) {
      throw new Error("media stream not ready");
    }
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) {
      throw new Error("WebAudio unavailable");
    }
    this.audioCtx = new AudioCtx();
    if (this.audioCtx.state === "suspended") {
      try {
        await this.audioCtx.resume();
      } catch (err) {
        console.warn("VoiceLipSync: resume error", err);
      }
    }
    this.analyser = this.audioCtx.createAnalyser();
    this.analyser.fftSize = 1024;
    this.analyser.smoothingTimeConstant = 0.6;
    this.data = new Float32Array(this.analyser.fftSize);
    this.sourceNode = this.audioCtx.createMediaStreamSource(this.mediaStream);
    this.sourceNode.connect(this.analyser);
  }

  stop() {
    if (!this.active) {
      return;
    }
    this.active = false;
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
    this.router.clear(SOURCE_ID);
    this.cleanupStream();
    this.analyser = null;
    this.data = null;
    this.smoothed = 0;
    this.intensity = 0;
    this.updateMeter(0);
    this.updateStatus("Mic idle");
    if (this.ui.start) {
      this.ui.start.disabled = false;
    }
    if (this.ui.stop) {
      this.ui.stop.disabled = true;
    }
  }

  cleanupStream() {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (err) {
          console.debug("VoiceLipSync: track stop skipped", err);
        }
      });
      this.mediaStream = null;
    }
    if (this.sourceNode) {
      try {
        this.sourceNode.disconnect();
      } catch (err) {
        console.debug("VoiceLipSync: source disconnect skipped", err);
      }
      this.sourceNode = null;
    }
    if (this.audioCtx) {
      try {
        this.audioCtx.close();
      } catch (err) {
        console.debug("VoiceLipSync: audioCtx close skipped", err);
      }
      this.audioCtx = null;
    }
  }

  tick() {
    if (!this.active || !this.analyser || !this.data) {
      return;
    }
    this.animationId = requestAnimationFrame(() => this.tick());
    this.analyser.getFloatTimeDomainData(this.data);
    let sumSquares = 0;
    for (let i = 0; i < this.data.length; i += 1) {
      const sample = this.data[i] || 0;
      sumSquares += sample * sample;
    }
    const rms = Math.sqrt(sumSquares / this.data.length);
    const adj = Math.max(0, rms - this.noiseFloor);
    const intensity = clamp(adj * this.gain, 0, 1);
    this.smoothed = this.smoothed * 0.7 + intensity * 0.3;
    this.intensity = this.intensity * 0.5 + this.smoothed * 0.5;
    this.updateMeter(this.intensity);

    const weights = this.buildVisemeWeights(this.intensity);
    this.router.route(SOURCE_ID, weights);

    const now = performance.now();
    if (!window.HUDVRM?.currentVRM?.expressionManager && now - this.lastReadyCheck > 2000) {
      this.updateStatus("Mic live — load a VRM avatar to render visemes");
      this.lastReadyCheck = now;
    }
  }

  buildVisemeWeights(level) {
    if (level <= 0.002) {
      return {
        A: 0,
        I: 0,
        U: 0,
        E: 0,
        O: 0,
      };
    }
    const base = clamp(level, 0, 1);
    const gentle = base * 0.65;
    const soft = base * 0.45;
    return {
      A: base,
      I: gentle,
      U: soft,
      E: base * 0.5,
      O: base * 0.55,
    };
  }
}

function init() {
  const controller = window.VoiceLipSync || new VoiceLipSyncController(routerInstance);
  controller.bindUi();
  window.VoiceLipSync = controller;
}

document.addEventListener("DOMContentLoaded", init, { once: true });
