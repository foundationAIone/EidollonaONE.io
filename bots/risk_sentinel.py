"""Risk sentinel bot enforcing max loss and other caps."""

from __future__ import annotations

from typing import Any, Dict

from .base_se_bot import SEAwareBot


class RiskSentinelBot(SEAwareBot):
    def __init__(self, policy: Dict[str, Any]):
        super().__init__("risk_sentinel", policy)

    def guard(self, snapshot: Dict[str, Any]) -> None:
        context = self.se_context()
        ok, reasons = self.se_gate(context)
        if not ok:
            self.emit(
                "policy_violation",
                decision="HOLD",
                reasons=reasons,
                se=context,
                snapshot=snapshot,
            )
            return
        max_daily_loss = float(snapshot.get("max_daily_loss_usd", 25))
        current = float(snapshot.get("daily_loss_usd", 0))
        if current <= -abs(max_daily_loss):
            self.emit(
                "kill_switch",
                decision="ALLOW",
                reasons=["daily_loss_hit"],
                se=context,
                snapshot=snapshot,
            )
        else:
            self.emit(
                "risk_snapshot",
                decision="ALLOW",
                reasons=["se_ready", "risk_ok"],
                se=context,
                snapshot=snapshot,
            )
