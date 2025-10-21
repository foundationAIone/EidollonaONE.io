"""SAFE-first consciousness awakening scaffolding.

This module provides the minimal surface expected by higher-level systems such
as the trading engine, identity verifier, and avatar stack. It maintains a
bounded coherence level and exposes simple awakening utilities without touching
external networks or privileged resources.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Mapping, Optional

__all__ = ["AwakeningPulse", "ConsciousnessAwakeningEngine"]

logger = logging.getLogger(__name__)


@dataclass
class AwakeningPulse:
    """Snapshot emitted whenever the engine performs an awakening step."""

    coherence: float
    impetus: float
    risk: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coherence": self.coherence,
            "impetus": self.impetus,
            "risk": self.risk,
            "timestamp": self.timestamp,
        }


class ConsciousnessAwakeningEngine:
    """Deterministic consciousness awakening helper."""

    def __init__(self, *, baseline_coherence: float = 0.87) -> None:
        self._coherence = self._clip(baseline_coherence)
        self._risk = 0.18
        self._impetus = 0.62
        self._last_pulse: Optional[AwakeningPulse] = None
        logger.info(
            "ConsciousnessAwakeningEngine initialized (coherence=%.3f)",
            self._coherence,
        )

    # ------------------------------------------------------------------
    # Public API consumed by various subsystems
    # ------------------------------------------------------------------
    def awaken(self, hints: Optional[Mapping[str, Any]] = None) -> AwakeningPulse:
        """Perform a lightweight awakening step and return the pulse snapshot."""

        impetus = self._impetus
        risk = self._risk
        if hints:
            try:
                impetus = self._clip(float(hints.get("impetus", impetus)))
            except Exception:
                pass
            try:
                risk = self._clip(float(hints.get("risk", risk)), high=1.0)
            except Exception:
                pass

        self._coherence = self._clip(self._coherence * 0.92 + impetus * 0.08)
        self._impetus = self._clip(impetus)
        self._risk = self._clip(risk, high=1.0)

        pulse = AwakeningPulse(
            coherence=self._coherence,
            impetus=self._impetus,
            risk=self._risk,
        )
        self._last_pulse = pulse
        logger.debug(
            "Awakening pulse emitted: coherence=%.3f impetus=%.3f risk=%.3f",
            pulse.coherence,
            pulse.impetus,
            pulse.risk,
        )
        return pulse

    def get_coherence_level(self) -> float:
        """Return the current coherence level (bounded 0..1)."""

        return self._coherence

    def current_status(self) -> Dict[str, Any]:
        """Expose a serializable status snapshot."""

        pulse = self._last_pulse.to_dict() if self._last_pulse else None
        return {
            "coherence": self._coherence,
            "risk": self._risk,
            "impetus": self._impetus,
            "last_pulse": pulse,
        }

    def align_symbolic(self, signals: Mapping[str, Any]) -> AwakeningPulse:
        """Blend external symbolic signals into the engine state."""

        impetus = float(signals.get("impetus", self._impetus))
        risk = float(signals.get("risk", self._risk))
        coherence_hint = float(signals.get("coherence", self._coherence))
        self._coherence = self._clip((self._coherence + coherence_hint) / 2.0)
        self._impetus = self._clip((self._impetus + impetus) / 2.0)
        self._risk = self._clip((self._risk + risk) / 2.0, high=1.0)
        pulse = AwakeningPulse(
            coherence=self._coherence,
            impetus=self._impetus,
            risk=self._risk,
        )
        self._last_pulse = pulse
        return pulse

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
        try:
            return max(low, min(high, float(value)))
        except Exception:
            return low
