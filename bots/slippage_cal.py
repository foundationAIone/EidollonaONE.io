"""Slippage calibrator bot that records nightly adjustments."""

from __future__ import annotations

from typing import Any, Dict

from .base_se_bot import SEAwareBot


class SlippageCalibratorBot(SEAwareBot):
    def __init__(self, policy: Dict[str, Any]):
        super().__init__("slippage_cal", policy)

    def nightly_update(self, samples: Dict[str, Any]) -> None:
        context = self.se_context()
        ok, reasons = self.se_gate(context)
        decision = "ALLOW" if ok else "HOLD"
        if ok:
            reasons = reasons + ["update_ok"]
        self.emit(
            "slippage_model_update",
            decision=decision,
            reasons=reasons,
            se=context,
            samples=samples,
        )
