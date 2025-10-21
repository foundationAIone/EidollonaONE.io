"""Pair selection bot for venue diversification."""

from __future__ import annotations

from typing import Any, Dict

from .base_se_bot import SEAwareBot
from .se_decorators import se_required


class PairSieveBot(SEAwareBot):
    def __init__(self, policy: Dict[str, Any]):
        super().__init__("pair_sieve", policy)

    @se_required(decision_event="pair_candidate")
    def evaluate(self, context, metrics: Dict[str, Any]) -> None:
        liquidity = float(metrics.get("liquidity", 0.0))
        cost = float(metrics.get("cost_bps", 10.0))
        latency_penalty = float(metrics.get("latency_penalty", 1.0))
        diversification = float(metrics.get("diversification", 0.5))
        venue_parity = float(metrics.get("venue_parity", 1.0))
        score = (
            0.35 * liquidity
            + 0.25 * (-cost)
            + 0.15 * (-latency_penalty)
            + 0.15 * diversification
            + 0.10 * venue_parity
        )
        threshold = float(self.policy.get("promote_threshold", 0.70))
        if score >= threshold:
            self.emit(
                "pair_promote",
                decision="ALLOW",
                reasons=["se_ready", "ra_ok", "risk_ok", "score_ok"],
                se=context,
                score=score,
                metrics=metrics,
            )
        else:
            self.emit(
                "pair_deny",
                decision="HOLD",
                reasons=["se_ready", "score_low"],
                se=context,
                score=score,
                metrics=metrics,
            )
