"""
quantum_probabilistic_information_rendering_system/system.py

SAFE, deterministic "Quantum Probabilistic Information Rendering" for EidollonaONE.

- Aligns with SE4.3 (Wings/Aletheia): Base-12 lotus + Wings W(t) + Reality Alignment RA(t)
- Falls back gracefully when SE4.3/quantum modules are not present
- Produces an auditable, HUD-ready snapshot:
    * signals (coherence, impetus, risk, readiness, wings, RA, gate12)
    * 12-phase ring (phase weights)
    * probability ribbons (histogram + percentiles) derived from impetus & risk
    * uncertainty cone summary
    * explicit "reasons" (wings/RA/gate drivers) for explainability
- Emits NDJSON audit events to $EIDOLLONA_AUDIT or logs/audit.ndjson

SAFE Posture:
- No PII; consent/verified-net are modeled via signals (RA) from the symbolic engine
- Never bypasses Gate₁₂ or policy; rendering is read-only and explainable
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import importlib

# --- Audit (fallback if utils.audit isn't available) -------------------------
def _audit_ndjson(event: str, **fields: Any) -> None:
    path = os.getenv("EIDOLLONA_AUDIT", "logs/audit.ndjson")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {"event": event, **fields, "ts": time.time()}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


try:
    # prefer project auditor if available
    from utils.audit import audit_ndjson as audit_ndjson  # type: ignore
except Exception:  # pragma: no cover
    audit_ndjson = _audit_ndjson  # fallback


# --- Symbolic signals loader (SE4.3 -> compat -> legacy) ---------------------
def _load_signals_obj() -> Any:
    """
    Returns an engine 'signals' object with attributes:
      coherence, impetus, risk, uncertainty, mirror_consistency, readiness,
      gate12 (float), gate12_array (list[float])?, wings (float)?, reality_alignment (float)?
    """
    # Preferred: loader that prefers SE4.3 (Wings/RA) if configured
    try:
        from symbolic_core.se_loader_ext import load_se_engine  # type: ignore

        engine = load_se_engine()
        if hasattr(engine, "evaluate"):
            context: Dict[str, Any] = {}
            if hasattr(engine, "seed_context"):
                context = engine.seed_context()  # type: ignore[attr-defined]
            elif hasattr(engine, "context_template"):
                context = engine.context_template()  # type: ignore[attr-defined]
            if not context:
                from symbolic_core.se43_wings import assemble_se43_context  # type: ignore

                context = assemble_se43_context()
            return engine.evaluate(context)  # type: ignore[attr-defined]

        return engine
    except Exception:
        pass
    # Fallback: direct SE4.3 (if available)
    try:
        from symbolic_core.se43_wings import SymbolicEquation43, assemble_se43_context  # type: ignore

        ctx = assemble_se43_context()
        return SymbolicEquation43().evaluate(ctx)
    except Exception:
        pass
    # Legacy: SE4.1 (no wings/RA)
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
    from symbolic_core.symbolic_equation import SymbolicEquation41  # type: ignore

    eng = SymbolicEquation41()
    return eng.evaluate(assemble_se41_context())


# --- Optional quantum cadence (12-phase) -------------------------------------
def _phase_map_from_quantum() -> Optional[Dict[int, float]]:
    """
    Try to read a 12-phase normalized map from QuantumBridge; return None if unavailable.
    """
    try:
        module = importlib.import_module(
            "ai_core.quantum_core.quantum_logic.quantum_bridge"
        )
        QuantumBridge = getattr(module, "QuantumBridge")  # type: ignore
        pm = QuantumBridge().phase_map()  # type: ignore
        return {int(k): float(v) for k, v in pm.phases.items()}
    except Exception:
        return None


# --- Config & Snapshot --------------------------------------------------------
@dataclass
class RenderConfig:
    bins: int = 41  # histogram resolution
    min_bins: int = 21  # enforce minimal deterministic resolution
    ewma_beta: float = 0.25  # smoothing for ring/metrics (0..1)
    include_wings: bool = True
    include_ra: bool = True
    # bounds used for visualization protection (SAFE clipping)
    clip_impetus_low: float = 0.0
    clip_impetus_high: float = 1.0

    def clamp_bins(self) -> int:
        return max(self.min_bins, int(self.bins))


@dataclass
class RenderSnapshot:
    timestamp: float
    signals: Dict[str, Any]
    ring: Dict[str, Any]  # { weights: list[float], labels: list[str] }
    probability: Dict[str, Any]  # { bins: list[float], hist: list[float], p10,p50,p90 }
    cone: Dict[str, Any]  # uncertainty cone (near/med/far)
    reasons: Dict[str, Any]  # wings/RA/gate drivers


# --- Main system --------------------------------------------------------------
class QPIRSystem:
    GATE_LABELS = [
        "consent",
        "privacy_pii",
        "power_caps",
        "auditability",
        "alignment",
        "data_integrity",
        "ext_policy",
        "counterparty_trust",
        "latency_compute",
        "tail_risk",
        "operator_override",
        "language_gate",
    ]

    def __init__(self, config: Optional[RenderConfig] = None) -> None:
        self.cfg = config or RenderConfig()
        # EWMA states
        self._last_ring: Optional[List[float]] = None
        self._last_impetus: Optional[float] = None

    # -- Public API -----------------------------------------------------------
    def render_snapshot(self) -> RenderSnapshot:
        """
        Compute a deterministic, HUD-ready snapshot and log an audit event.
        """
        sig = _load_signals_obj()
        sigd = self._signals_to_dict(sig)

        # Phase ring: prefer quantum cadence; else derive from signals
        ring_weights = self._derive_ring(sig)
        ring_labels = self.GATE_LABELS[: len(ring_weights)]

        # Probability histogram from (impetus, risk)
        impetus = float(sigd.get("impetus", 0.0))
        risk = float(sigd.get("risk", 1.0))
        bins, hist, p10, p50, p90 = self._probability_view(impetus, risk)

        # Uncertainty cone
        cone = self._uncertainty_cone(
            uncertainty=float(sigd.get("uncertainty", 0.0)),
            ra=float(sigd.get("reality_alignment", 0.0) if self.cfg.include_ra else 0.0),
        )

        # Reasons
        reasons = self._reasons(sig, ring_weights, (p10, p50, p90))

        snapshot = RenderSnapshot(
            timestamp=time.time(),
            signals=sigd,
            ring={"weights": ring_weights, "labels": ring_labels},
            probability={"bins": bins, "hist": hist, "p10": p10, "p50": p50, "p90": p90},
            cone=cone,
            reasons=reasons,
        )

        audit_ndjson(
            "qpir_snapshot",
            signals=sigd,
            ring=snapshot.ring,
            probability={"p10": p10, "p50": p50, "p90": p90},
            reasons=reasons,
        )
        return snapshot

    def to_hud_payload(self, snap: RenderSnapshot) -> Dict[str, Any]:
        """
        Convert snapshot into a minimal JSON payload for UI consumption.
        """
        return {
            "ts": snap.timestamp,
            "signals": snap.signals,
            "ring": snap.ring,
            "probability": snap.probability,
            "cone": snap.cone,
            "reasons": snap.reasons,
        }

    # -- Internals ------------------------------------------------------------
    def _derive_ring(self, sig: Any) -> List[float]:
        """
        12-phase normalized ring; smooth with EWMA for visual stability.
        """
        pm = _phase_map_from_quantum()
        if pm:
            raw = [pm.get(i, 0.0) for i in range(1, 13)]
        else:
            # Derive from Gates + coherence/risk if cadence unavailable
            arr = getattr(sig, "gate12_array", None)
            if not isinstance(arr, list) or len(arr) == 0:
                arr = [1.0] * 12
            coh = float(getattr(sig, "coherence", 0.0))
            rsk = float(getattr(sig, "risk", 1.0))
            base = max(1e-6, coh * (1.0 - rsk))
            raw = [max(0.0, min(1.0, float(x))) * base for x in arr[:12]]

        s = sum(raw) or 1.0
        norm = [x / s for x in raw]

        # EWMA smoothing
        if self._last_ring is None:
            self._last_ring = norm
            return norm
        beta = max(0.0, min(1.0, self.cfg.ewma_beta))
        sm = [(1 - beta) * p + beta * q for p, q in zip(self._last_ring, norm)]
        self._last_ring = sm
        return sm

    def _probability_view(
        self, impetus: float, risk: float
    ) -> Tuple[List[float], List[float], float, float, float]:
        """Render histogram percentiles using a deterministic Beta fit."""
        m = max(0.0, min(1.0, impetus))
        kappa = 2.0 + 10.0 * max(0.0, min(1.0, (1.0 - risk)))
        alpha = max(1e-3, m * kappa)
        beta = max(1e-3, (1.0 - m) * kappa)

        n = self.cfg.clamp_bins()
        xs = [i / (n - 1) for i in range(n)]

        def beta_pdf(x: float) -> float:
            if x <= 0.0 or x >= 1.0:
                x = max(1e-6, min(1.0 - 1e-6, x))
            return (x ** (alpha - 1.0)) * ((1.0 - x) ** (beta - 1.0))

        pdf = [beta_pdf(x) for x in xs]
        s = sum(pdf) or 1.0
        hist = [p / s for p in pdf]

        cdf = 0.0
        p10 = p50 = p90 = 0.0
        for x, h in zip(xs, hist):
            cdf += h
            if cdf >= 0.10 and p10 == 0.0:
                p10 = x
            if cdf >= 0.50 and p50 == 0.0:
                p50 = x
            if cdf >= 0.90 and p90 == 0.0:
                p90 = x
        return xs, hist, p10, p50, p90

    def _uncertainty_cone(self, *, uncertainty: float, ra: float) -> Dict[str, Any]:
        """
        Three-band "cone": near/medium/far uncertainty scores (0..1), adjusted by RA.
        Higher RA reduces perceived uncertainty.
        """
        u = self._clip(uncertainty, 0.0, 1.0)
        ra_adj = self._clip(ra, 0.0, 1.0)
        damp = 1.0 - 0.35 * ra_adj  # up to 35% reduction in cone with strong RA
        near = self._clip(u * 0.85 * damp, 0.0, 1.0)
        med = self._clip(u * 1.00 * damp, 0.0, 1.0)
        far = self._clip(u * 1.15 * damp, 0.0, 1.0)
        return {
            "near": round(near, 4),
            "medium": round(med, 4),
            "far": round(far, 4),
            "ra_damping": round(damp, 4),
        }

    def _reasons(
        self, sig: Any, ring: List[float], pct: Tuple[float, float, float]
    ) -> Dict[str, Any]:
        """
        Human-parsable reasons supporting the snapshot.
        """
        wings = float(getattr(sig, "wings", 1.0) or 1.0)
        ra = float(getattr(sig, "reality_alignment", 0.0) or 0.0)
        risk = float(getattr(sig, "risk", 1.0))
        coh = float(getattr(sig, "coherence", 0.0))
        gate = float(getattr(sig, "gate12", 1.0))
        labels = self.GATE_LABELS

        # dominant gate segments by weight
        top = sorted([(i, w) for i, w in enumerate(ring)], key=lambda t: t[1], reverse=True)[:3]
        top_gates = [{"label": labels[i], "weight": round(w, 4)} for i, w in top]

        return {
            "wings_active": wings >= 1.03,
            "wings_value": round(wings, 4),
            "reality_alignment": round(ra, 4),
            "risk": round(risk, 4),
            "coherence": round(coh, 4),
            "gate12": round(gate, 4),
            "dominant_gates": top_gates,
            "percentiles": {
                "p10": round(pct[0], 4),
                "p50": round(pct[1], 4),
                "p90": round(pct[2], 4),
            },
        }

    # --- Math helpers --------------------------------------------------------
    @staticmethod
    def _signals_to_dict(sig: Any) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k in (
            "coherence",
            "impetus",
            "risk",
            "uncertainty",
            "mirror_consistency",
            "readiness",
            "gate12",
            "wings",
            "reality_alignment",
            "gamma",
        ):
            v = getattr(sig, k, None)
            if v is not None:
                try:
                    out[k] = float(v) if isinstance(v, (int, float)) else v
                except Exception:
                    out[k] = v
        # Optional: gate array
        arr = getattr(sig, "gate12_array", None)
        if isinstance(arr, list):
            out["gate12_array"] = [float(x) for x in arr[:12]]
        return out

    @staticmethod
    def _clip(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, float(x)))


# --- CLI smoke ----------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    qpir = QPIRSystem()
    snap = qpir.render_snapshot()
    payload = qpir.to_hud_payload(snap)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
