"""
ai_core.probabilistic_quantum_rendering.models

Typed surface models for SAFE QPIR snapshots.

The QPIR system (see :mod:`quantum_probabilistic_information_rendering_system`)
emits dictionaries/dataclasses containing probability, ring, and signal data.
This module upgrades those loosely typed payloads into ergonomic dataclasses
that downstream renderers (ASCII, HUDs, tests) can consume without scattering
parsing logic throughout the codebase.

Highlights
~~~~~~~~~~
* Compatible with direct ``RenderSnapshot`` instances or raw dictionaries.
* Preserves SAFE posture (read-only, no mutation, explainability-friendly).
* Provides helpers for fetching live snapshots when the QPIR system is
  available, along with graceful fallbacks when it is not.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

try:
	from quantum_probabilistic_information_rendering_system import (  # type: ignore
		QPIRSystem,
		RenderConfig,
		RenderSnapshot,
	)
except Exception:  # pragma: no cover - module optional during bootstrap
	QPIRSystem = None  # type: ignore[assignment]
	RenderConfig = None  # type: ignore[assignment]
	RenderSnapshot = None  # type: ignore[assignment]


if TYPE_CHECKING:
	from quantum_probabilistic_information_rendering_system import (  # type: ignore
		RenderConfig as RenderConfigType,
		RenderSnapshot as RenderSnapshotType,
	)
else:  # pragma: no cover - typing fallback
	RenderConfigType = Any
	RenderSnapshotType = Any


__all__ = [
	"SignalFrame",
	"RingGate",
	"RingSnapshot",
	"ProbabilityRibbon",
	"UncertaintyCone",
	"ReasonBundle",
	"QPIRSnapshotModel",
	"fetch_snapshot_model",
]


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
_CORE_SIGNAL_KEYS = {
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
}


def _safe_float(value: Any, default: float = 0.0) -> float:
	try:
		return float(value)
	except (TypeError, ValueError):
		return float(default)


def _optional_float(value: Any) -> Optional[float]:
	try:
		return float(value)
	except (TypeError, ValueError):  # includes None
		return None


def _ensure_list(seq: Optional[Sequence[Any]]) -> List[Any]:
	if seq is None:
		return []
	return list(seq)


# ---------------------------------------------------------------------------
# Core dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SignalFrame:
	"""Primary SE4.3 signals governing the probability snapshot."""

	coherence: float
	impetus: float
	risk: float
	uncertainty: float
	readiness: str
	wings: float
	reality_alignment: float
	gate12: float
	mirror_consistency: Optional[float] = None
	gamma: Optional[float] = None
	extra: Dict[str, Any] = field(default_factory=dict)

	@classmethod
	def from_payload(cls, data: Optional[Dict[str, Any]]) -> "SignalFrame":
		payload = dict(data or {})
		return cls(
			coherence=_safe_float(payload.get("coherence")),
			impetus=_safe_float(payload.get("impetus")),
			risk=_safe_float(payload.get("risk"), 1.0),
			uncertainty=_safe_float(payload.get("uncertainty")),
			readiness=str(payload.get("readiness", "warming")),
			wings=_safe_float(payload.get("wings"), 1.0),
			reality_alignment=_safe_float(payload.get("reality_alignment")),
			gate12=_safe_float(payload.get("gate12"), 1.0),
			mirror_consistency=_optional_float(payload.get("mirror_consistency")),
			gamma=_optional_float(payload.get("gamma")),
			extra={k: v for k, v in payload.items() if k not in _CORE_SIGNAL_KEYS},
		)


@dataclass(frozen=True)
class RingGate:
	"""Single gate contribution in the 12-phase lotus."""

	label: str
	weight: float


@dataclass(frozen=True)
class RingSnapshot:
	"""Normalized gate weights for the 12-phase (Gate₁₂) ring."""

	gates: List[RingGate] = field(default_factory=list)

	@property
	def weights(self) -> List[float]:
		return [gate.weight for gate in self.gates]

	@property
	def labels(self) -> List[str]:
		return [gate.label for gate in self.gates]

	def top(self, count: int = 3) -> List[RingGate]:
		count = max(0, count)
		return sorted(self.gates, key=lambda g: g.weight, reverse=True)[:count]

	@classmethod
	def from_payload(cls, data: Optional[Dict[str, Any]]) -> "RingSnapshot":
		payload = data or {}
		weights = [
			_safe_float(w)
			for w in _ensure_list(payload.get("weights"))
		]
		labels = _ensure_list(payload.get("labels"))
		gates: List[RingGate] = []
		for idx, weight in enumerate(weights):
			label = str(labels[idx]) if idx < len(labels) else f"gate_{idx + 1}"
			gates.append(RingGate(label=label, weight=weight))
		return cls(gates=gates)


@dataclass(frozen=True)
class ProbabilityRibbon:
	"""Histogram + percentile view derived from impetus/risk."""

	bins: List[float]
	density: List[float]
	p10: float
	p50: float
	p90: float

	@classmethod
	def from_payload(cls, data: Optional[Dict[str, Any]]) -> "ProbabilityRibbon":
		payload = data or {}
		bins = [_safe_float(x) for x in _ensure_list(payload.get("bins"))]
		hist = [_safe_float(x) for x in _ensure_list(payload.get("hist"))]
		return cls(
			bins=bins,
			density=hist,
			p10=_safe_float(payload.get("p10"), bins[0] if bins else 0.0),
			p50=_safe_float(payload.get("p50"), bins[len(bins) // 2] if bins else 0.0),
			p90=_safe_float(payload.get("p90"), bins[-1] if bins else 1.0),
		)


@dataclass(frozen=True)
class UncertaintyCone:
	"""Near/medium/far uncertainty bands, RA-damped."""

	near: float
	medium: float
	far: float
	ra_damping: Optional[float] = None

	@classmethod
	def from_payload(cls, data: Optional[Dict[str, Any]]) -> "UncertaintyCone":
		payload = data or {}
		return cls(
			near=_safe_float(payload.get("near")),
			medium=_safe_float(payload.get("medium")),
			far=_safe_float(payload.get("far")),
			ra_damping=_optional_float(payload.get("ra_damping")),
		)


@dataclass(frozen=True)
class ReasonBundle:
	"""Explainability metadata emitted alongside the snapshot."""

	wings_active: bool
	wings_value: float
	reality_alignment: float
	gate12: float
	dominant_gates: List[RingGate] = field(default_factory=list)
	percentiles: Tuple[float, float, float] = (0.0, 0.0, 0.0)
	extra: Dict[str, Any] = field(default_factory=dict)

	@classmethod
	def from_payload(cls, data: Optional[Dict[str, Any]]) -> "ReasonBundle":
		payload = dict(data or {})
		dom_payload = payload.get("dominant_gates") or []
		dominant = [
			RingGate(
				label=str(item.get("label", f"gate_{idx + 1}")),
				weight=_safe_float(item.get("weight")),
			)
			for idx, item in enumerate(dom_payload)
			if isinstance(item, dict)
		]
		pct = payload.get("percentiles") or {}
		return cls(
			wings_active=bool(payload.get("wings_active", False)),
			wings_value=_safe_float(payload.get("wings_value"), 1.0),
			reality_alignment=_safe_float(payload.get("reality_alignment")),
			gate12=_safe_float(payload.get("gate12"), 1.0),
			dominant_gates=dominant,
			percentiles=(
				_safe_float(pct.get("p10")),
				_safe_float(pct.get("p50")),
				_safe_float(pct.get("p90")),
			),
			extra={
				k: v
				for k, v in payload.items()
				if k not in {"wings_active", "wings_value", "reality_alignment", "gate12", "dominant_gates", "percentiles"}
			},
		)


# ---------------------------------------------------------------------------
# Aggregate snapshot model
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class QPIRSnapshotModel:
	"""Typed representation of a QPIR snapshot (timestamp + rich payload)."""

	timestamp: float
	signals: SignalFrame
	ring: RingSnapshot
	probability: ProbabilityRibbon
	cone: UncertaintyCone
	reasons: ReasonBundle
	raw: Dict[str, Any] = field(default_factory=dict)

	@classmethod
	def from_dict(cls, payload: Dict[str, Any]) -> "QPIRSnapshotModel":
		return cls(
			timestamp=_safe_float(payload.get("ts"), time.time()),
			signals=SignalFrame.from_payload(payload.get("signals")),
			ring=RingSnapshot.from_payload(payload.get("ring")),
			probability=ProbabilityRibbon.from_payload(payload.get("probability")),
			cone=UncertaintyCone.from_payload(payload.get("cone")),
			reasons=ReasonBundle.from_payload(payload.get("reasons")),
			raw=dict(payload),
		)

	@classmethod
	def from_snapshot(cls, snap: Any) -> "QPIRSnapshotModel":
		if snap is None:
			raise ValueError("Snapshot cannot be None")
		if RenderSnapshot is not None and isinstance(snap, RenderSnapshot):  # type: ignore[arg-type]
			payload = {
				"ts": snap.timestamp,
				"signals": snap.signals,
				"ring": snap.ring,
				"probability": snap.probability,
				"cone": snap.cone,
				"reasons": snap.reasons,
			}
		elif isinstance(snap, dict):
			payload = snap
		else:
			payload = {
				"ts": getattr(snap, "timestamp", time.time()),
				"signals": getattr(snap, "signals", {}),
				"ring": getattr(snap, "ring", {}),
				"probability": getattr(snap, "probability", {}),
				"cone": getattr(snap, "cone", {}),
				"reasons": getattr(snap, "reasons", {}),
			}
		return cls.from_dict(payload)

	def to_payload(self) -> Dict[str, Any]:
		"""Return a dictionary matching the original QPIR payload schema."""

		return {
			"ts": self.timestamp,
			"signals": {**self.signals.extra, **self._signal_core_dict()},
			"ring": {
				"weights": self.ring.weights,
				"labels": self.ring.labels,
			},
			"probability": {
				"bins": self.probability.bins,
				"hist": self.probability.density,
				"p10": self.probability.p10,
				"p50": self.probability.p50,
				"p90": self.probability.p90,
			},
			"cone": {
				"near": self.cone.near,
				"medium": self.cone.medium,
				"far": self.cone.far,
				"ra_damping": self.cone.ra_damping,
			},
			"reasons": {
				"wings_active": self.reasons.wings_active,
				"wings_value": self.reasons.wings_value,
				"reality_alignment": self.reasons.reality_alignment,
				"gate12": self.reasons.gate12,
				"dominant_gates": [
					{"label": gate.label, "weight": gate.weight}
					for gate in self.reasons.dominant_gates
				],
				"percentiles": {
					"p10": self.reasons.percentiles[0],
					"p50": self.reasons.percentiles[1],
					"p90": self.reasons.percentiles[2],
				},
				**self.reasons.extra,
			},
		}

	def _signal_core_dict(self) -> Dict[str, Any]:
		core = {
			"coherence": self.signals.coherence,
			"impetus": self.signals.impetus,
			"risk": self.signals.risk,
			"uncertainty": self.signals.uncertainty,
			"readiness": self.signals.readiness,
			"wings": self.signals.wings,
			"reality_alignment": self.signals.reality_alignment,
			"gate12": self.signals.gate12,
		}
		if self.signals.mirror_consistency is not None:
			core["mirror_consistency"] = self.signals.mirror_consistency
		if self.signals.gamma is not None:
			core["gamma"] = self.signals.gamma
		return core


# ---------------------------------------------------------------------------
# Convenience fetcher
# ---------------------------------------------------------------------------
def fetch_snapshot_model(config: Optional[RenderConfigType] = None) -> QPIRSnapshotModel:
	"""Instantiate a QPIR system (if available) and return a typed snapshot."""

	if QPIRSystem is None:
		raise ImportError(
			"QPIRSystem is not available. Ensure quantum_probabilistic_information_rendering_system is installed."
		)
	system = QPIRSystem(config) if config is not None else QPIRSystem()  # type: ignore[call-arg]
	snap = system.render_snapshot()
	return QPIRSnapshotModel.from_snapshot(snap)


