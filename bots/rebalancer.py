"""Inventory rebalancer with SE gating."""

from __future__ import annotations

from typing import Any, Dict

from .base_se_bot import SEAwareBot


class RebalancerBot(SEAwareBot):
    def __init__(self, policy: Dict[str, Any]):
        super().__init__("rebalancer", policy)

    def rebalance(self, inventories: Dict[str, Any]) -> None:
        context = self.se_context()
        ok, reasons = self.se_gate(context)
        slack = float(self.policy.get("target_slack_pct", 0.10))
        decision = "ALLOW" if ok else "HOLD"
        reason_payload = reasons if not ok else reasons + ["rebalance_ok"]
        self.emit(
            "rebalance_execute",
            decision=decision,
            reasons=reason_payload,
            se=context,
            inventories=inventories,
            slack=slack,
        )
