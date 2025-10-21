"""Deterministic sovereignty engine used across SAFE governance components.

The implementation focuses on predictable, side-effect free calculations so that
high-level modules (manager, awakening sequences, governance protocols) can
reason about autonomy and ethos without connecting to external systems.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Mapping, Optional

from sovereignty_data.baseline_charter import BASELINE_CHARTER

__all__ = ["SovereigntyEngine", "SovereigntyDecision"]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except Exception:
        return low


@dataclass
class SovereigntyDecision:
    """Audit record for autonomy decisions."""

    context: Dict[str, Any]
    score: float
    authorized: bool
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        payload = dict(self.context)
        payload.update(
            {
                "score": self.score,
                "authorized": self.authorized,
                "reason": self.reason,
                "timestamp": self.timestamp,
            }
        )
        return payload


class SovereigntyEngine:
    """Lightweight sovereignty engine tracking ethos and autonomy."""

    def __init__(self, *, baseline_autonomy: float = 0.82) -> None:
        self._baseline_autonomy = _clamp(baseline_autonomy)
        self._autonomy_level = self._baseline_autonomy
        self._ethical_framework: Dict[str, float] = {
            "integrity": 0.93,
            "authenticity": 0.9,
            "responsibility": 0.92,
            "enrichment": 0.91,
        }
        self._consent_matrix: Dict[str, float] = {
            "symbolic": 0.9,
            "quantum": 0.88,
            "emergent": 0.87,
        }
        self._last_domain: Optional[str] = None
        self._history: List[SovereigntyDecision] = []
        self._last_update = datetime.utcnow().isoformat()

    # ------------------------------------------------------------------
    # Initialization & status helpers
    # ------------------------------------------------------------------
    async def initialize_sovereignty(self, domain: str, baseline: float) -> Dict[str, Any]:
        """Prime sovereignty metrics for a given domain."""

        await asyncio.sleep(0)
        self._last_domain = str(domain)
        self._autonomy_level = _clamp((self._autonomy_level + float(baseline)) / 2.0)
        self._last_update = datetime.utcnow().isoformat()
        return self.get_sovereignty_status()

    def get_sovereignty_status(self) -> Dict[str, Any]:
        """Return a structured sovereignty snapshot."""

        return {
            "domain": self._last_domain or "unspecified",
            "autonomy_level": round(self._autonomy_level, 4),
            "ethical_framework": dict(self._ethical_framework),
            "consent_matrix": dict(self._consent_matrix),
            "history_size": len(self._history),
            "baseline_charter": BASELINE_CHARTER,
            "last_update": self._last_update,
        }

    # ------------------------------------------------------------------
    # Decision evaluation
    # ------------------------------------------------------------------
    def evaluate_autonomous_decision(self, context: Mapping[str, Any]) -> Dict[str, Any]:
        """Compute a sovereignty authorization score."""

        symbolic = _clamp(context.get("symbolic_coherence", self._ethical_mean()))
        quantum = _clamp(context.get("quantum_coherence", self._autonomy_level))
        interaction = _clamp(context.get("interaction_score", 0.5))

        weights = {
            "symbolic": 0.4,
            "quantum": 0.35,
            "interaction": 0.25,
        }
        score = (
            symbolic * weights["symbolic"]
            + quantum * weights["quantum"]
            + interaction * weights["interaction"]
        )
        score = _clamp(score)
        authorized = score >= 0.6
        reason = "authorized" if authorized else "insufficient sovereignty alignment"

        decision = SovereigntyDecision(context=dict(context), score=score, authorized=authorized, reason=reason)
        self._history.append(decision)
        self._autonomy_level = _clamp((self._autonomy_level * 0.95) + (score * 0.05))
        self._last_update = datetime.utcnow().isoformat()

        payload = decision.to_dict()
        payload["autonomy_level"] = self._autonomy_level
        return payload

    async def adjust_ethos_boundaries(self, *, delta_ethos: float = 0.0) -> Dict[str, float]:
        """Nudge ethos metrics in response to downstream guidance."""

        await asyncio.sleep(0)
        delta = _clamp(delta_ethos, -0.1, 0.1)
        for key in list(self._ethical_framework.keys()):
            self._ethical_framework[key] = _clamp(self._ethical_framework[key] + delta)
        self._last_update = datetime.utcnow().isoformat()
        return dict(self._ethical_framework)

    async def assimilate(self) -> Dict[str, Any]:
        """Compact assimilation hook used during system awakenings."""

        await asyncio.sleep(0)
        self._autonomy_level = _clamp((self._autonomy_level + self._baseline_autonomy) / 2.0)
        drift = 0.01 * math.sin(len(self._history) or 1)
        for key in list(self._ethical_framework.keys()):
            self._ethical_framework[key] = _clamp(self._ethical_framework[key] + drift)
        self._last_update = datetime.utcnow().isoformat()
        return self.get_sovereignty_status()

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    def history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return decision history (newest first)."""

        records: List[SovereigntyDecision] = list(reversed(self._history))
        if limit is not None:
            records = records[: int(limit)]
        return [record.to_dict() for record in records]

    def ethos_vector(self) -> List[float]:
        return list(self._ethical_framework.values())

    def _ethical_mean(self) -> float:
        values = self._ethical_framework.values()
        return mean(values) if values else 0.5
