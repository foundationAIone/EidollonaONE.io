"""Sovereignty Engine core with SymbolicEquation integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency
	from symbolic_core.symbolic_equation41 import SymbolicEquation41  # type: ignore
except Exception:  # pragma: no cover

	class SymbolicEquation41:  # type: ignore
		def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, float]:
			return {
				"risk": float(ctx.get("risk_hint", 0.4)),
				"uncertainty": float(ctx.get("uncertainty_hint", 0.4)),
				"coherence": float(ctx.get("coherence_hint", 0.6)),
			}


def _clamp01(value: float) -> float:
	return max(0.0, min(1.0, value))


@dataclass
class SovereigntyStatus:
	phase: str = "idle"
	stability: float = 0.7
	legitimacy_score: float = 0.8
	coherence: float = 0.65
	last_update: str = field(default_factory=lambda: datetime.utcnow().isoformat())
	signals: Dict[str, float] = field(default_factory=dict)

	def to_dict(self) -> Dict[str, Any]:
		return {
			"phase": self.phase,
			"stability": self.stability,
			"legitimacy_score": self.legitimacy_score,
			"coherence": self.coherence,
			"last_update": self.last_update,
			"signals": dict(self.signals),
		}


class SovereigntyEngine:
	"""Lightweight governance coherence engine."""

	def __init__(self, symbolic: Optional[SymbolicEquation41] = None) -> None:
		self._symbolic = symbolic or SymbolicEquation41()
		self._status = SovereigntyStatus()

	@staticmethod
	def _signals_to_dict(signals: Any) -> Dict[str, float]:
		if hasattr(signals, "to_dict"):
			try:
				converted = signals.to_dict()  # type: ignore[attr-defined]
			except Exception:
				converted = None
			if isinstance(converted, dict):
				filtered: Dict[str, float] = {}
				for key, value in converted.items():
					if isinstance(value, (int, float)):
						filtered[str(key)] = float(value)
				return filtered
		if isinstance(signals, dict):
			filtered = {
				str(key): float(value)
				for key, value in signals.items()
				if isinstance(value, (int, float))
			}
			return filtered
		return {}

	def initialize_sovereignty(self, channel: str, activation_level: float) -> None:
		"""Initialize sovereignty systems with symbolic tuning."""
		activation_level = _clamp01(float(activation_level))
		context = {
			"risk_hint": _clamp01(0.25 + activation_level * 0.3),
			"uncertainty_hint": _clamp01(0.35 - activation_level * 0.2),
			"coherence_hint": _clamp01(0.55 + activation_level * 0.4),
			"channel": channel,
			"activation_level": activation_level,
		}
		signals = self._symbolic.evaluate(context)
		signals_dict = self._signals_to_dict(signals)
		self._status = SovereigntyStatus(
			phase="initialized",
			stability=_clamp01(0.65 + activation_level * 0.25),
			legitimacy_score=_clamp01(0.7 + activation_level * 0.2),
			coherence=_clamp01(signals_dict.get("coherence", 0.6)),
			signals=signals_dict,
		)

	async def assimilate(self) -> None:  # pragma: no cover - async noop hook
		self._status.phase = "assimilating"
		self._status.last_update = datetime.utcnow().isoformat()

	def update_context(self, **kwargs: Any) -> None:
		"""Refresh symbolic context incrementally."""
		new_context = {
			"risk_hint": kwargs.get("risk_hint", self._status.signals.get("risk", 0.4)),
			"uncertainty_hint": kwargs.get(
				"uncertainty_hint", self._status.signals.get("uncertainty", 0.4)
			),
			"coherence_hint": kwargs.get(
				"coherence_hint", self._status.signals.get("coherence", 0.6)
			),
		}
		signals = self._symbolic.evaluate(new_context)
		signals_dict = self._signals_to_dict(signals)
		self._status.signals = signals_dict
		self._status.coherence = _clamp01(signals_dict.get("coherence", 0.6))
		self._status.stability = _clamp01(
			self._status.stability * 0.7 + signals_dict.get("coherence", 0.6) * 0.3
		)
		self._status.last_update = datetime.utcnow().isoformat()

	def get_sovereignty_status(self) -> Dict[str, Any]:
		return self._status.to_dict()

	def to_dict(self) -> Dict[str, Any]:
		return self.get_sovereignty_status()
