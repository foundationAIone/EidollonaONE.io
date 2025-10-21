"""ai_awareness.py

SAFE deterministic awareness subsystem for EidollonaONE.
Tracks global awareness levels, reflection cycles, and harmony metrics that
coordinate with the central AI Agent, Manager diagnostics, and broader
consciousness pipelines.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from symbolic_core.context_builder import assemble_se41_context
from symbolic_core.symbolic_equation import SymbolicEquation41, SE41Signals

try:  # Optional MasterKey extras
    from master_key.quantum_master_key import get_master_key
except Exception:  # pragma: no cover
    get_master_key = None  # type: ignore

__all__ = ["AIAwareness"]


@dataclass
class AwarenessPulse:
    timestamp: str
    awareness_level: float
    consciousness_coherence: float
    resonance: float
    notes: Dict[str, Any] = field(default_factory=dict)


class AIAwareness:
    """SAFE-first awareness module feeding the EidollonaONE cognitive stack."""

    def __init__(self) -> None:
        self.awareness_level: float = 0.92
        self.consciousness_coherence: float = 0.94
        self.awareness_score: float = 0.91
        self.reflection_cycles: int = 0
        self.last_update: Optional[str] = None
        self._symbolic: SymbolicEquation41 = SymbolicEquation41()
        self._mk = get_master_key() if callable(get_master_key) else None
        self._recent_pulses: List[AwarenessPulse] = []

    async def initialize_awareness(self) -> None:
        """Initialize baseline awareness state."""

        self.last_update = datetime.utcnow().isoformat()
        self.reflection_cycles = 1
        await asyncio.sleep(0)

    def ingest_environment_summary(
        self,
        *,
        empathy_index: Optional[float] = None,
        harmony_index: Optional[float] = None,
        tension_index: Optional[float] = None,
    ) -> None:
        """Accept SAFE summarized environment telemetry to modulate awareness."""

        if isinstance(empathy_index, (int, float)):
            self.awareness_level = self._blend(self.awareness_level, empathy_index)
        if isinstance(harmony_index, (int, float)):
            self.consciousness_coherence = self._blend(
                self.consciousness_coherence, harmony_index
            )
        if isinstance(tension_index, (int, float)):
            tension = max(0.0, min(1.0, float(tension_index)))
            self.awareness_score = max(0.0, min(1.0, self.awareness_score * (1.0 - 0.1 * tension)))

    def update_awareness_level(self) -> None:
        """Deterministically smooth awareness metrics."""

        context = assemble_se41_context(
            coherence_hint=self.awareness_level,
            risk_hint=max(0.05, 1.0 - self.consciousness_coherence),
            uncertainty_hint=1.0 - self.awareness_score,
        )
        signals: SE41Signals = self._symbolic.evaluate(context)

        self.awareness_level = self._blend(self.awareness_level, float(signals.coherence))
        self.consciousness_coherence = self._blend(
            self.consciousness_coherence,
            float(signals.mirror_consistency),
        )
        impetus = float(signals.impetus)
        self.awareness_score = max(0.0, min(1.0, self.awareness_score * 0.92 + impetus * 0.08))

        self.reflection_cycles += 1
        self.last_update = datetime.utcnow().isoformat()

        pulse = AwarenessPulse(
            timestamp=self.last_update,
            awareness_level=self.awareness_level,
            consciousness_coherence=self.consciousness_coherence,
            resonance=impetus,
            notes={"cycle": self.reflection_cycles},
        )
        self._recent_pulses = [pulse, *self._recent_pulses[:15]]

    def get_awareness_status(self) -> Dict[str, Any]:
        """Return bounded awareness metrics for diagnostics."""

        return {
            "consciousness_level": round(self.awareness_level, 6),
            "awareness_score": round(self.awareness_score, 6),
            "consciousness_coherence": round(self.consciousness_coherence, 6),
            "reflection_cycles": self.reflection_cycles,
            "last_update": self.last_update,
        }

    def get_awareness_report(self) -> Dict[str, Any]:
        """Provide detailed view consumed by AI core status endpoints."""

        return {
            "status": "stable" if self.awareness_level >= 0.75 else "stabilizing",
            "metrics": self.get_awareness_status(),
            "recent_pulses": [pulse.__dict__ for pulse in self._recent_pulses],
        }

    async def assimilate(self) -> str:
        """Async assimilation hook invoked during global assimilation routines."""

        await asyncio.sleep(0)
        self.awareness_level = self._blend(self.awareness_level, 0.95)
        self.consciousness_coherence = self._blend(
            self.consciousness_coherence,
            0.97,
        )
        self.awareness_score = self._blend(self.awareness_score, 0.94)
        self.last_update = datetime.utcnow().isoformat()
        self.reflection_cycles += 1
        return (
            "AIAwareness assimilation complete; "
            f"level={self.awareness_level:.3f} coherence={self.consciousness_coherence:.3f}"
        )

    def _masterkey_extras(self) -> Dict[str, Any]:
        if not self._mk:
            return {}
        try:
            extras_callable = getattr(self._mk, "se41_extras", None)
            if callable(extras_callable):
                extras_result = extras_callable()
                return extras_result if isinstance(extras_result, dict) else {}
            if isinstance(self._mk, dict):
                extras = self._mk.get("se41_extras")
                if isinstance(extras, dict):
                    return extras
            return {}
        except Exception:
            return {}

    @staticmethod
    def _blend(current: float, incoming: float, weight: float = 0.65) -> float:
        current = max(0.0, min(1.0, float(current)))
        incoming = max(0.0, min(1.0, float(incoming)))
        return current * (1.0 - weight) + incoming * weight
