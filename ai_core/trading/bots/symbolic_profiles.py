"""Symbolic profile helpers for `ai_core/trading/bots`."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from symbolic_core.symbolic_equation import SymbolicEquation41

__all__ = ["SymbolicProfile", "build_profile", "DEFAULT_PROFILE"]


@dataclass
class SymbolicProfile:
    name: str
    context: Dict[str, Any]
    signals: Dict[str, Any]
    equation: SymbolicEquation41 = field(default_factory=SymbolicEquation41, repr=False)

    def next_signal(self, **overrides: Any) -> Dict[str, Any]:
        ctx = dict(self.context)
        ctx.update(overrides)
        return self.equation.evaluate(ctx).to_dict()


_BASE_CONTEXT = {
    "coherence_hint": 0.84,
    "risk_hint": 0.16,
    "uncertainty_hint": 0.21,
    "mirror": {"consistency": 0.81},
    "metadata": {"package": "ai_core/trading/bots"},
}


def build_profile(name: str, **context_overrides: Any) -> SymbolicProfile:
    ctx = dict(_BASE_CONTEXT)
    ctx.update(context_overrides)
    equation = SymbolicEquation41()
    signals = equation.evaluate(ctx).to_dict()
    return SymbolicProfile(name=name, context=ctx, signals=signals, equation=equation)


DEFAULT_PROFILE = build_profile("default")
