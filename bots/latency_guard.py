"""Latency guard bot that toggles venues based on health metrics."""

from __future__ import annotations

from typing import Any, Dict

from .base_se_bot import SEAwareBot


class LatencyGuardBot(SEAwareBot):
    def __init__(self, policy: Dict[str, Any]):
        super().__init__("latency_guard", policy)

    def check(self, metrics: Dict[str, Any]) -> None:
        context = self.se_context()
        ok, reasons = self.se_gate(context)
        rtt = float(metrics.get("rest_rtt_ms", 0))
        lag = float(metrics.get("ws_lag_ms", 0))
        error_rate = float(metrics.get("err_rate", 0))
        if not ok:
            self.emit(
                "latency_alert",
                decision="HOLD",
                reasons=reasons,
                se=context,
                metrics=metrics,
            )
            return
        if (
            rtt > float(self.policy.get("rtt_p95_ms", 300))
            or lag > float(self.policy.get("ws_lag_ms", 250))
            or error_rate > float(self.policy.get("err_rate", 0.01))
        ):
            self.emit(
                "venue_disable",
                decision="ALLOW",
                reasons=["se_ready", "venue_degraded"],
                se=context,
                metrics=metrics,
            )
        else:
            self.emit(
                "venue_enable",
                decision="ALLOW",
                reasons=["se_ready", "venue_ok"],
                se=context,
                metrics=metrics,
            )
