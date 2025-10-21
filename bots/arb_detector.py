"""Arbitrage detector bot that respects SE governance."""

from __future__ import annotations

from typing import Any, Dict

from .base_se_bot import SEAwareBot
from .se_decorators import se_required


class ArbDetectorBot(SEAwareBot):
    def __init__(self, policy: Dict[str, Any]):
        super().__init__("arb_detector", policy)

    @se_required(decision_event="arb_opportunity")
    def detect_and_propose(self, context, books: Dict[str, Any]) -> None:
        edge_bps = float(books.get("net_edge_bps", 0.0))
        min_edge = float(self.policy.get("min_edge_bps", 15.0))
        if edge_bps >= min_edge:
            ttl = 60 if context.wings >= 1.03 else 45
            order = {
                "symbol": books.get("symbol", "BTC/USD"),
                "maker_ttl": ttl,
                "ioc_dev_bps_cap": float(self.policy.get("taker_cap_bps", 50)),
                "net_edge_bps": edge_bps,
                "route": books.get("route", "kraken->coinbase"),
            }
            self.emit(
                "q_execute",
                decision="ALLOW",
                reasons=["se_ready", "ra_ok", "risk_ok", "net_edge_ok"],
                se=context,
                order=order,
            )
        else:
            self.emit(
                "arb_opportunity",
                decision="HOLD",
                reasons=["se_ready", "ra_ok", "risk_ok", "edge_low"],
                se=context,
            )
