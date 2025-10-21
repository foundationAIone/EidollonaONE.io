"""Risk-aware harmonic budget allocator for quantum cadence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

try:
    from utils.audit import audit_ndjson
except Exception:  # pragma: no cover
    def audit_ndjson(event: str, **payload: Any) -> None:  # type: ignore
        return None

from .quantum_logic.quantum_bridge import PhaseMap

__all__ = ["HarmonicBudget", "HarmonicProcessor"]


@dataclass
class HarmonicBudget:
    total: float
    per_phase: List[float]
    risk_buffer: float
    slack: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": round(self.total, 6),
            "per_phase": [round(v, 6) for v in self.per_phase],
            "risk_buffer": round(self.risk_buffer, 6),
            "slack": round(self.slack, 6),
            "metadata": dict(self.metadata),
        }


class HarmonicProcessor:
    def __init__(self, *, floor: float = 0.12) -> None:
        self._floor = max(0.0, float(floor))

    def allocate(
        self,
        phase_map: PhaseMap,
        *,
        plan: Optional[Mapping[str, Any]] = None,
    ) -> HarmonicBudget:
        sig = phase_map.signals
        impetus = self._clamp(sig.get("impetus", 0.0))
        wings = self._clamp(sig.get("wings", 1.0), hi=1.06)
        ra = self._clamp(sig.get("reality_alignment", 0.0))
        risk = self._clamp(sig.get("risk", 0.0))

        base_total = max(self._floor, impetus * (1.0 - risk) * wings * max(0.5, ra + 0.1))
        total = self._clamp(base_total)
        risk_buffer = self._clamp(risk * 0.25)
        slack = self._clamp(1.0 - total - risk_buffer)

        weights = [phase_map.phases.get(idx + 1, 0.0) for idx in range(12)]
        if not weights or sum(weights) <= 0.0:
            weights = [1.0 / 12.0] * 12
        per_phase = [total * w for w in weights]

        metadata = {
            "readiness": phase_map.readiness,
            "gate": phase_map.gate,
            "plan_id": (plan or {}).get("id"),
        }

        budget = HarmonicBudget(
            total=total,
            per_phase=per_phase,
            risk_buffer=risk_buffer,
            slack=slack,
            metadata=metadata,
        )
        audit_ndjson(
            "q_harmonic_budget",
            readiness=phase_map.readiness,
            gate=phase_map.gate,
            total=total,
            risk_buffer=risk_buffer,
            slack=slack,
        )
        return budget

    @staticmethod
    def _clamp(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
        try:
            num = float(value)
        except Exception:
            return float(lo)
        if num < lo:
            return float(lo)
        if num > hi:
            return float(hi)
        return float(num)
