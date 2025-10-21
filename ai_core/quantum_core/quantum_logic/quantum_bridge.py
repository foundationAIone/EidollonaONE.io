"""Quantum cadence bridge for SE4.3 Wings/Aletheia."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .quantum_symbolic_bridge import BridgeReport, QSimConfig, QuantumSymbolicBridge

try:
	from utils.audit import audit_ndjson
except Exception:  # pragma: no cover
	def audit_ndjson(event: str, **payload: Any) -> None:  # type: ignore
		return None

try:
	from symbolic_core.se_loader_ext import load_se_engine  # type: ignore
except Exception:  # pragma: no cover
	load_se_engine = None  # type: ignore

try:
	from symbolic_core.se43_wings import SymbolicEquation43, assemble_se43_context  # type: ignore
except Exception:  # pragma: no cover
	SymbolicEquation43 = None  # type: ignore
	assemble_se43_context = None  # type: ignore

try:
	from symbolic_core.symbolic_equation import SymbolicEquation41  # type: ignore
	from symbolic_core.context_builder import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover
	SymbolicEquation41 = None  # type: ignore
	assemble_se41_context = None  # type: ignore

__all__ = [
	"QuantumSymbolicBridge",
	"QSimConfig",
	"BridgeReport",
	"PhaseMap",
	"QuantumBridge",
]


@dataclass
class PhaseMap:
	phases: Dict[int, float]
	readiness: str
	gate: str
	signals: Dict[str, Any]
	timestamp: float


class QuantumBridge:
	"""Produce Base-12 phase maps suitable for quantum cadence alignment."""

	def __init__(self, *, smoothing_beta: float = 0.25) -> None:
		self._smoothing_beta = max(0.0, min(1.0, float(smoothing_beta)))
		self._last: Optional[Dict[int, float]] = None

	def phase_map(self, context: Optional[Mapping[str, Any]] = None) -> PhaseMap:
		signals = self._load_signals(context)
		ring = signals.get("gate12_array") or [1.0] * 12
		weights = self._normalize(ring)
		if self._last is None:
			smoothed = weights
		else:
			beta = self._smoothing_beta
			smoothed = [
				beta * current + (1.0 - beta) * self._last.get(idx + 1, current)
				for idx, current in enumerate(weights)
			]
		self._last = {idx + 1: smoothed[idx] for idx in range(len(smoothed))}
		readiness = str(signals.get("readiness", "warming"))
		gate = str(signals.get("gate_state", signals.get("gate", "HOLD")))
		snapshot = PhaseMap(
			phases=dict(self._last),
			readiness=readiness,
			gate=gate,
			signals=signals,
			timestamp=time.time(),
		)
		audit_ndjson(
			"q_phase_map",
			readiness=readiness,
			gate=gate,
			wings=signals.get("wings"),
			reality_alignment=signals.get("reality_alignment"),
			phases=snapshot.phases,
		)
		return snapshot

	# ------------------------------------------------------------------
	def _normalize(self, values: Iterable[Any]) -> List[float]:
		data = [max(0.0, float(v)) for v in list(values)[:12]]
		if not data:
			data = [1.0] * 12
		total = sum(data) or 1.0
		return [v / total for v in data]

	def _load_signals(self, context: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
		# Preferred: loader with internal history management
		if load_se_engine is not None:
			try:
				sig = load_se_engine(context=context)  # type: ignore[arg-type]
				return self._signals_to_dict(sig)
			except Exception:
				pass

		if SymbolicEquation43 is not None and assemble_se43_context is not None:
			try:
				ctx = assemble_se43_context(**dict(context or {}))
				sig = SymbolicEquation43().evaluate(ctx)
				return self._signals_to_dict(sig)
			except Exception:
				pass

		if SymbolicEquation41 is not None and assemble_se41_context is not None:
			ctx = assemble_se41_context()
			sig = SymbolicEquation41().evaluate(ctx)
			return self._signals_to_dict(sig)

		# Fallback to deterministic defaults
		return {
			"coherence": 0.8,
			"impetus": 0.55,
			"risk": 0.2,
			"uncertainty": 0.25,
			"readiness": "warming",
			"gate_state": "HOLD",
			"wings": 1.0,
			"reality_alignment": 0.8,
			"gate12_array": [1.0] * 12,
		}

	@staticmethod
	def _signals_to_dict(sig: Any) -> Dict[str, Any]:
		out: Dict[str, Any] = {}
		for attr in (
			"coherence",
			"impetus",
			"risk",
			"uncertainty",
			"mirror_consistency",
			"readiness",
			"gate_state",
			"gate12",
			"wings",
			"reality_alignment",
			"gamma",
		):
			value = getattr(sig, attr, None)
			if value is not None:
				out[attr] = float(value) if isinstance(value, (int, float)) else value
		arr = getattr(sig, "gate12_array", None)
		if isinstance(arr, list):
			out["gate12_array"] = [float(x) for x in arr[:12]]
		return out
