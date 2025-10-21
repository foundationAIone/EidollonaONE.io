"""Awakening utilities for sovereignty alignment during SAFE bootstraps."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

__all__ = ["AwakeningPulse", "SovereigntyAwakeningEngine"]


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except Exception:
        return low


@dataclass
class AwakeningPulse:
    coherence: float
    sovereignty_level: float
    impetus: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coherence": self.coherence,
            "sovereignty_level": self.sovereignty_level,
            "impetus": self.impetus,
            "timestamp": self.timestamp,
        }


class SovereigntyAwakeningEngine:
    """Minimal engine coordinating sovereignty awakening pulses."""

    def __init__(self) -> None:
        self._activation_level = 0.75
        self._coherence = 0.8
        self._impetus = 0.7
        self._last_pulse: Optional[AwakeningPulse] = None

    async def awaken(self, *, boost: float = 0.05) -> AwakeningPulse:
        await asyncio.sleep(0)
        self._activation_level = _clip(self._activation_level + boost)
        self._coherence = _clip(self._coherence + boost / 2.0)
        self._impetus = _clip(self._impetus + boost / 1.5)
        pulse = AwakeningPulse(
            coherence=self._coherence,
            sovereignty_level=self._activation_level,
            impetus=self._impetus,
        )
        self._last_pulse = pulse
        return pulse

    def current_status(self) -> Dict[str, Any]:
        pulse = self._last_pulse.to_dict() if self._last_pulse else None
        return {
            "activation_level": self._activation_level,
            "coherence": self._coherence,
            "impetus": self._impetus,
            "last_pulse": pulse,
        }

    async def calm(self, *, damping: float = 0.02) -> AwakeningPulse:
        await asyncio.sleep(0)
        self._activation_level = _clip(self._activation_level - damping)
        self._coherence = _clip(self._coherence - damping / 2.0)
        self._impetus = _clip(self._impetus - damping / 1.5)
        pulse = AwakeningPulse(
            coherence=self._coherence,
            sovereignty_level=self._activation_level,
            impetus=self._impetus,
        )
        self._last_pulse = pulse
        return pulse
