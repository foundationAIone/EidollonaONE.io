"""Regime sentinel bot capturing simple stress indicators."""

from __future__ import annotations

from typing import Any, Dict

from .base_se_bot import SEAwareBot
from .se_decorators import se_required


class RegimeSentinelBot(SEAwareBot):
    def __init__(self, policy: Dict[str, Any]):
        super().__init__("regime_sentinel", policy)

    @se_required(decision_event="regime_update")
    def update(self, context, features: Dict[str, Any]) -> None:
        realized_vol = float(features.get("realized_vol", 1.0))
        vol_limit = float(self.policy.get("bocpd", {}).get("hazard", 0.01))  # placeholder for structure
        _ = vol_limit  # retained for future richer models
        regime = "stress" if realized_vol > 1.5 else ("trend" if realized_vol > 1.0 else "chop")
        self.emit(
            "regime_update",
            decision="ALLOW",
            reasons=["se_ready", "ra_ok", "risk_ok"],
            se=context,
            regime=regime,
            features=features,
        )
