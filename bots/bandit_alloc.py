"""Bandit allocator bot implementing a bounded reweight update."""

from __future__ import annotations

from typing import Dict

from .base_se_bot import SEAwareBot
from .se_decorators import se_required


class BanditAllocatorBot(SEAwareBot):
    def __init__(self, policy: Dict[str, float]):
        super().__init__("bandit_alloc", policy)
        self.weights: Dict[str, float] = {}

    @se_required(decision_event="alloc_update")
    def reweight(self, context, performance: Dict[str, float]) -> None:
        step = float(self.policy.get("max_step_per_day", 0.05))
        if not performance:
            self.emit(
                "alloc_update",
                decision="HOLD",
                reasons=["se_ready", "no_strategies"],
                se=context,
            )
            return
        if not self.weights:
            base = 1.0 / max(1, len(performance))
            self.weights = {key: base for key in performance}
        avg = sum(performance.values()) / max(1, len(performance))
        for key, value in performance.items():
            delta = step * ((value - avg) / (abs(avg) + 1e-6))
            self.weights[key] = max(0.0, min(1.0, self.weights.get(key, 0.0) + delta))
        total = sum(self.weights.values()) or 1.0
        for key in list(self.weights):
            self.weights[key] /= total
        self.emit(
            "alloc_update",
            decision="ALLOW",
            reasons=["se_ready", "ra_ok", "risk_ok"],
            se=context,
            weights=self.weights,
        )
