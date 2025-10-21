"""Probabilistic quantum rendering public surface.

This package exposes SAFE, deterministic helpers for interacting with the
probabilistic quantum information rendering stack.  When the upstream QPIR
system is available we delegate to the orchestration utilities contained in
``renderer.py``; otherwise we provide SymbolicEquation41-driven fallbacks so
tests, HUDs, and diagnostics can continue functioning without external
dependencies.

Highlights
~~~~~~~~~~
* Analyzer-friendly re-exports (:class:`~.renderer.QPIRRenderer` et al.).
* ``symbolic_snapshot`` builds a ``QPIRSnapshotModel`` from SE41 baseline
  signals, ensuring repeatable, SAFE paper-mode behaviour.
* ``symbolic_payload`` and ``symbolic_ascii_block`` provide HUD/ASCII-ready
  payloads suitable for CLI drills or NDJSON audit trails.

The entire module is read-only and SAFE-aligned—no hardware access, no
side-effects beyond optional logging performed by downstream callers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from symbolic_core.symbolic_equation import SymbolicEquation41

from .models import QPIRSnapshotModel, RingSnapshot
from .renderer import (
	QPIRRenderer,
	hud_payload,
	print_ascii_snapshot,
	render_ascii_block,
	snapshot_model,
)

__all__ = [
	"QPIRRenderer",
	"snapshot_model",
	"hud_payload",
	"render_ascii_block",
	"print_ascii_snapshot",
	"symbolic_snapshot",
	"symbolic_payload",
	"symbolic_ascii_block",
]


# ---------------------------------------------------------------------------
# Symbolic fallback helpers
# ---------------------------------------------------------------------------
_SE41 = SymbolicEquation41()
_RING_LABELS: Tuple[str, ...] = tuple(f"gate_{idx}" for idx in range(1, 13))


def _baseline_context() -> Dict[str, Any]:
	return {
		"coherence_hint": 0.84,
		"risk_hint": 0.18,
		"uncertainty_hint": 0.23,
		"mirror": {"consistency": 0.8},
		"substrate": {"S_EM": 0.86},
		"ethos_hint": {
			"authenticity": 0.91,
			"integrity": 0.9,
			"responsibility": 0.89,
			"enrichment": 0.92,
		},
		"metadata": {"source": "symbolic_fallback"},
	}


def _normalize(values: Iterable[float]) -> List[float]:
	seq = [max(0.0, float(v)) for v in values]
	total = sum(seq) or 1.0
	return [v / total for v in seq]


def _ring_from_signals(signals: Dict[str, Any]) -> Dict[str, Any]:
	coherence = float(signals.get("coherence", 0.8))
	risk = float(signals.get("risk", 0.2))
	wings = float(signals.get("wings", 0.95))
	base = max(0.05, coherence - 0.3 * risk)
	raw = [base - 0.02 * abs(idx - 5.5) + 0.01 * wings for idx in range(12)]
	weights = [round(v, 6) for v in _normalize(raw)]
	return {"weights": weights, "labels": list(_RING_LABELS)}


def _probability_ribbon(signals: Dict[str, Any]) -> Dict[str, Any]:
	impetus = float(signals.get("impetus", 0.5))
	risk = float(signals.get("risk", 0.2))
	bins = [-1.0, -0.5, 0.0, 0.5, 1.0]
	density_raw = [risk * 0.4, risk * 0.2, max(0.05, 1.0 - risk - impetus * 0.3), impetus * 0.3, impetus * 0.1]
	density = [round(v, 6) for v in _normalize(density_raw)]
	return {
		"bins": bins,
		"hist": density,
		"p10": bins[1],
		"p50": bins[2] + impetus * 0.25,
		"p90": bins[3] + (1.0 - risk) * 0.25,
	}


def _uncertainty(signals: Dict[str, Any]) -> Dict[str, Any]:
	uncertainty = float(signals.get("uncertainty", 0.25))
	reality_alignment = float(signals.get("reality_alignment", 0.82))
	near = uncertainty
	medium = near + (1.0 - reality_alignment) * 0.15
	far = medium + (1.0 - reality_alignment) * 0.2
	return {
		"near": round(near, 6),
		"medium": round(medium, 6),
		"far": round(far, 6),
		"ra_damping": round(reality_alignment, 6),
	}


def _reasons(signals: Dict[str, Any], ring: Dict[str, Any], ribbon: Dict[str, Any]) -> Dict[str, Any]:
	top_gates = RingSnapshot.from_payload(ring).top(3)
	p10 = ribbon.get("p10", 0.0)
	p50 = ribbon.get("p50", 0.0)
	p90 = ribbon.get("p90", 0.0)
	return {
		"wings_active": bool(signals.get("wings", 0.0) > 0.7),
		"wings_value": float(signals.get("wings", 0.9)),
		"reality_alignment": float(signals.get("reality_alignment", 0.82)),
		"gate12": float(signals.get("gate12", 0.88)),
		"dominant_gates": [
			{"label": gate.label, "weight": gate.weight}
			for gate in top_gates
		],
		"percentiles": {"p10": p10, "p50": p50, "p90": p90},
	}


def symbolic_snapshot(timestamp: Optional[float] = None) -> QPIRSnapshotModel:
	"""Return a deterministic QPIR snapshot derived from SymbolicEquation41."""

	ctx = _baseline_context()
	signals_payload = _SE41.evaluate(ctx).to_dict()
	signals_payload.setdefault("readiness", "ready")
	signals_payload.setdefault("wings", 0.93)
	signals_payload.setdefault("reality_alignment", signals_payload.get("coherence", 0.83))
	signals_payload.setdefault("gate12", 0.9)

	ring_payload = _ring_from_signals(signals_payload)
	prob_payload = _probability_ribbon(signals_payload)
	cone_payload = _uncertainty(signals_payload)
	reason_payload = _reasons(signals_payload, ring_payload, prob_payload)

	payload = {
		"ts": float(timestamp if timestamp is not None else datetime.now(timezone.utc).timestamp()),
		"signals": signals_payload,
		"ring": ring_payload,
		"probability": prob_payload,
		"cone": cone_payload,
		"reasons": reason_payload,
	}

	return QPIRSnapshotModel.from_dict(payload)


def symbolic_payload() -> Dict[str, Any]:
	"""Return a HUD-ready dictionary constructed from ``symbolic_snapshot``."""

	return symbolic_snapshot().to_payload()


def symbolic_ascii_block() -> str:
	"""Render the symbolic snapshot as an ASCII block using local renderer."""

	snapshot = symbolic_snapshot()
	return QPIRRenderer().ascii_block(snapshot)
