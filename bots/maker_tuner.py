"""Maker quote planning bot with SE guardrails."""

from __future__ import annotations

from typing import Any, Dict

from .base_se_bot import SEAwareBot
from .se_decorators import se_required


class MakerTunerBot(SEAwareBot):
    def __init__(self, policy: Dict[str, Any]):
        super().__init__("maker_tuner", policy)

    @se_required(decision_event="maker_quote_plan")
    def plan_quotes(self, context, state: Dict[str, Any]) -> None:
        spread = float(state.get("spread_bps", 3.0))
        volatility = float(state.get("vol", 1.0))
        inventory = float(state.get("inventory", 0.0))
        aversion = float(self.policy.get("inv_aversion", 0.30))
        offset_bps = max(0.5, spread / 2.0 + 2.0 * volatility - aversion * abs(inventory))
        ttl_range = self.policy.get("ttl_range", [45, 90])
        ttl = max(min(int(ttl_range[-1]), 90), int(ttl_range[0]))
        self.emit(
            "maker_quote_post",
            decision="ALLOW",
            reasons=["se_ready", "ra_ok", "risk_ok"],
            se=context,
            quotes={"offset_bps": round(offset_bps, 2), "ttl": ttl},
        )
