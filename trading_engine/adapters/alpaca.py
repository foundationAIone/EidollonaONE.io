"""Paper Alpaca broker adapter stub."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class AlpacaAdapter:
    venue: str = "alpaca"
    spread_bps: float = 12.0
    latency_ms: float = 140.0
    fees_bps: float = 1.8

    def quote(self, symbol: str) -> Dict[str, object]:
        mid = self._mid(symbol)
        half = mid * self.spread_bps / 2e4
        return {
            "venue": self.venue,
            "symbol": symbol,
            "bid": round(mid - half, 2),
            "ask": round(mid + half, 2),
            "bid_size": 0.8,
            "ask_size": 0.9,
            "latency_ms": self.latency_ms,
            "fees_bps": self.fees_bps,
        }

    def submit_order(self, order: Dict[str, object]) -> Dict[str, object]:
        order_id = f"AL-{abs(hash((order.get('symbol'), order.get('side'), order.get('quantity')))) % 10**6:06d}"
        return {"venue": self.venue, "accepted": True, "order_id": order_id, "message": "paper_fill"}

    def _mid(self, symbol: str) -> float:
        reference: Dict[str, float] = {"BTC/USD": 30240.0, "ETH/USD": 1895.0}
        return reference.get(symbol.upper(), 1000.0) * (1.0 + 0.0003 * (time.time() % 0.1))


__all__ = ["AlpacaAdapter"]
