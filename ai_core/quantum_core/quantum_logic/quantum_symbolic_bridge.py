"""Sovereign-aligned quantum ↔ symbolic bridge for SAFE simulations."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

__all__ = ["QuantumSymbolicBridge", "QSimConfig", "BridgeReport"]

# ---------------------------------------------------------------------------
# Sovereign helpers (prefer canonical SE41 extension when available)
try:  # pragma: no cover - import-time capability check
    from symbolic_core.se41_ext import clamp01 as _se41_clamp01
    from symbolic_core.se41_ext import ethos_avg as _se41_ethos_avg
    from symbolic_core.se41_ext import road_map as _se41_road_map

    def clamp01(value: float) -> float:
        return float(_se41_clamp01(value))

    def ethos_avg(ethos: Dict[str, float]) -> float:
        return float(_se41_ethos_avg(ethos))

    def road_map(
        coherence: float,
        impetus: float,
        risk: float,
        uncertainty: float,
        ouro: float,
    ) -> Dict[str, str]:
        return _se41_road_map(
            coherence=coherence,
            impetus=impetus,
            risk=risk,
            uncertainty=uncertainty,
            ouro=ouro,
        )

except Exception:  # pragma: no cover - lightweight fallbacks for dev shells

    def clamp01(value: float) -> float:
        try:
            numeric = float(value)
        except Exception:
            return 0.0
        if numeric < 0.0:
            return 0.0
        if numeric > 1.0:
            return 1.0
        return numeric

    def ethos_avg(ethos: Dict[str, float]) -> float:
        if not ethos:
            return 0.0
        values = [float(v) for v in ethos.values()]
        return clamp01(sum(values) / max(1, len(values)))

    def road_map(
        coherence: float,
        impetus: float,
        risk: float,
        uncertainty: float,
        ouro: float,
    ) -> Dict[str, str]:
        coherence = clamp01(coherence)
        impetus = clamp01(impetus)
        risk = clamp01(risk)
        uncertainty = clamp01(uncertainty)
        ouro = clamp01(ouro)
        if coherence >= 0.75 and risk <= 0.20 and ouro <= 0.35:
            return {"sovereign_gate": "ROAD", "gate": "ALLOW"}
        if coherence >= 0.60 and risk <= 0.35 and ouro <= 0.55:
            return {"sovereign_gate": "SHOULDER", "gate": "REVIEW"}
        return {"sovereign_gate": "OFFROAD", "gate": "HOLD"}

# ---------------------------------------------------------------------------
# Auditing helpers (SAFE posture: never fail when logging)
try:  # pragma: no cover - optional dependency
    from utils.audit import audit_ndjson as _audit
except Exception:  # pragma: no cover - silent fallback for development

    def _audit(event: str, **payload: Any) -> None:
        return None


@dataclass
class QSimConfig:
    """Simulation-only quantum configuration derived from SE41 signals."""

    shots: int
    depth: int
    noise: float  # 0..1 (aggregate depolarizing proxy)
    entangle: float  # 0..1 (coupling strength)
    optimize: bool
    backend: str = "local_sim"
    notes: str = "SE41-derived config (simulation-only)"


@dataclass
class BridgeReport:
    """High-level outcome of the bridge computation."""

    sovereign_gate: str  # ROAD / SHOULDER / OFFROAD
    gate: str  # ALLOW / REVIEW / HOLD
    ready: bool
    config: QSimConfig
    fidelity_est: float
    rec: str  # human-readable recommendation
    params: Dict[str, float]  # echoes key SE41 / ethos values used


class QuantumSymbolicBridge:
    """Sovereign-aligned bridge from SE41 → bounded quantum simulations."""

    def __init__(self, *, name: str = "QuantumSymbolicBridge") -> None:
        self.name = name

    # ------------------------------------------------------------------
    # Public API
    def align(
        self,
        signals: Dict[str, Any],
        *,
        ouroboros: float = 0.0,
        explain: bool = True,
    ) -> BridgeReport:
        """Produce a sovereign-gated :class:`BridgeReport` from SE41 signals."""

        sig = self._sanitize_signals(signals)
        cfg = self._se41_to_qsim(sig)

        gate_map = road_map(
            sig["coherence"],
            sig["impetus"],
            sig["risk"],
            sig["uncertainty"],
            clamp01(ouroboros),
        )
        sovereign_gate = gate_map["sovereign_gate"]
        gate = gate_map["gate"]
        ready = gate == "ALLOW"

        fidelity = self._simulate_fidelity(cfg, sig)
        rec = self._recommend(sovereign_gate, gate, fidelity, sig, cfg)

        params = {
            "coherence": sig["coherence"],
            "impetus": sig["impetus"],
            "risk": sig["risk"],
            "uncertainty": sig["uncertainty"],
            "mirror_consistency": sig["mirror_consistency"],
            "S_EM": sig["S_EM"],
            "ethos_avg": ethos_avg(sig.get("ethos", {})),
        }

        report = BridgeReport(
            sovereign_gate=sovereign_gate,
            gate=gate,
            ready=ready,
            config=cfg,
            fidelity_est=fidelity,
            rec=rec,
            params=params,
        )

        _audit(
            "qbridge_align",
            signals=sig,
            ouroboros=clamp01(ouroboros),
            gate=gate,
            sovereign_gate=sovereign_gate,
            config=asdict(cfg),
            fidelity=fidelity,
            rec=rec,
        )

        if explain:
            # Hook for callers to provide additional narration/logging if desired.
            pass
        return report

    def to_job_spec(
        self,
        signals: Dict[str, Any],
        *,
        provider: str = "null",
        caps: Optional[Dict[str, float]] = None,
        ouroboros: float = 0.0,
    ) -> Dict[str, Any]:
        """Return a SAFE, bounded cluster job spec that mirrors :class:`QSimConfig`."""

        sig = self._sanitize_signals(signals)
        cfg = self._se41_to_qsim(sig)

        gpu_scale = max(1, int(round(4 * sig["coherence"] + 2 * sig["impetus"])))
        hours = 1.0 if sig["coherence"] >= 0.75 else 2.0

        spec = {
            "job": "qsim_align",
            "provider": provider,
            "resources": {"gpu": gpu_scale, "hours": hours, "mem_gb": 32.0},
            "data": {"signals": sig, "ouroboros": clamp01(ouroboros)},
            "output": {"bucket_out": "s3://simulated/qbridge/outputs"},
            "caps": caps or {"cost_usd_max": 250.0, "hours_max": 3.0},
            "audit": {"operator": "programmerONE", "gate": "ALLOW"},
        }
        _audit("qbridge_job_spec", spec=spec, qsim_config=asdict(cfg))
        return spec

    # ------------------------------------------------------------------
    # Helpers
    def _sanitize_signals(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        coherence = clamp01(raw.get("coherence", 0.0))
        impetus = clamp01(raw.get("impetus", 0.0))
        risk = clamp01(raw.get("risk", 1.0))
        uncertainty = clamp01(raw.get("uncertainty", 1.0))
        mirror = clamp01(raw.get("mirror_consistency", 0.0))
        s_em = clamp01(raw.get("S_EM", 0.0))
        ethos = raw.get("ethos") or {}
        return {
            "coherence": coherence,
            "impetus": impetus,
            "risk": risk,
            "uncertainty": uncertainty,
            "mirror_consistency": mirror,
            "S_EM": s_em,
            "ethos": ethos,
        }

    def _se41_to_qsim(self, sig: Dict[str, Any]) -> QSimConfig:
        coherence = sig["coherence"]
        impetus = sig["impetus"]
        risk = sig["risk"]
        uncertainty = sig["uncertainty"]
        mirror = sig["mirror_consistency"]

        shots = int(256 + 1536 * clamp01(0.7 * coherence + 0.3 * impetus))
        depth = int(8 + 40 * (1.0 - clamp01(0.6 * risk + 0.4 * (1.0 - coherence))))
        noise = clamp01(0.6 * risk + 0.4 * uncertainty)
        entangle = clamp01(0.2 + 0.8 * mirror)
        optimize = bool(coherence >= 0.75 and risk <= 0.20)

        return QSimConfig(
            shots=shots,
            depth=depth,
            noise=noise,
            entangle=entangle,
            optimize=optimize,
            backend="local_sim",
            notes="SE41-derived config (simulation-only)",
        )

    def _simulate_fidelity(self, cfg: QSimConfig, sig: Dict[str, Any]) -> float:
        coherence = sig["coherence"]
        impetus = sig["impetus"]
        risk = sig["risk"]
        uncertainty = sig["uncertainty"]
        mirror = sig["mirror_consistency"]
        s_em = sig["S_EM"]

        base = (
            0.55 * coherence
            + 0.20 * impetus
            + 0.10 * mirror
            + 0.10 * s_em
            + 0.05 * (1.0 - uncertainty)
            + 0.05 * (1.0 - risk)
        )
        penalty = 0.35 * cfg.noise + 0.10 * (1.0 - min(1.0, cfg.entangle))
        return clamp01(base - penalty + (0.02 if cfg.optimize else 0.0))

    def _recommend(
        self,
        sovereign_gate: str,
        gate: str,
        fidelity: float,
        sig: Dict[str, Any],
        cfg: QSimConfig,
    ) -> str:
        risk = sig["risk"]
        uncertainty = sig["uncertainty"]
        if gate == "HOLD" or sovereign_gate == "OFFROAD":
            return (
                "OFFROAD/HOLD: stabilize risk (approx %.2f) and uncertainty (approx %.2f) or lower noise before any "
                "cluster bursts; use EMP resonance drills and review ouroboros metrics."
                % (risk, uncertainty)
            )
        if gate == "REVIEW" or sovereign_gate == "SHOULDER":
            return (
                "SHOULDER/REVIEW: run paper simulations only; shallow circuits (depth≤%d), "
                "cap shots at %d, and recheck SE41 after resilience drill."
                % (min(cfg.depth, 16), min(cfg.shots, 512))
            )
        if fidelity >= 0.7:
            return (
                "ROAD/ALLOW: parameters look favorable (fidelity ~ %.2f). You may prepare a small "
                "q-sim batch or a bounded cluster job via to_job_spec() with cost caps."
                % fidelity
            )
        return (
            "ROAD/ALLOW but moderate fidelity (approx %.2f): keep circuits shallow, limit runtime, "
            "and re-evaluate after a short paper loop."
            % fidelity
        )
