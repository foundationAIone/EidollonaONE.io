"""Symbolic profile helpers for `ai_core/bots/trading/bot`."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from symbolic_core.symbolic_equation import SymbolicEquation41

__all__ = ["SymbolicProfile", "build_profile", "DEFAULT_PROFILE"]


@dataclass(slots=True)
class SymbolicProfile:
    name: str
    context: Dict[str, Any]
    signals: Dict[str, Any]

    def next_signal(self, **overrides: Any) -> Dict[str, Any]:
        ctx = dict(self.context)
        ctx.update(overrides)
        return SymbolicEquation41().evaluate(ctx).to_dict()


_BASE_CONTEXT = {
    "coherence_hint": 0.84,
    "risk_hint": 0.16,
    "uncertainty_hint": 0.21,
    "mirror": {"consistency": 0.81},
    "metadata": {"package": "ai_core/bots/trading/bot"},
}


def build_profile(name: str, **context_overrides: Any) -> SymbolicProfile:
    ctx = dict(_BASE_CONTEXT)
    ctx.update(context_overrides)
    signals = SymbolicEquation41().evaluate(ctx).to_dict()
    return SymbolicProfile(name=name, context=ctx, signals=signals)


DEFAULT_PROFILE = build_profile("default")
