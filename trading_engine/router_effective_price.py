"""Lightweight effective price router used by the SE4.3 paper cycle."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple


Quote = Dict[str, Any]
Order = Dict[str, Any]
Ack = Dict[str, Any]


class VenueAdapter(Protocol):
    venue: str

    def quote(self, symbol: str) -> Quote:
        ...

    def submit_order(self, order: Order) -> Ack:
        ...


class EffectivePriceRouter:
    """Aggregates venue quotes and computes a blended effective price."""

    def __init__(self, adapters: Iterable[VenueAdapter]):
        self._adapters: Dict[str, VenueAdapter] = {adapter.venue: adapter for adapter in adapters}

    # ------------------------------------------------------------------
    def adapters(self) -> Sequence[str]:
        return tuple(self._adapters.keys())

    def quotes(self, symbol: str) -> List[Quote]:
        ladder: List[Quote] = []
        for adapter in self._adapters.values():
            try:
                ladder.append(adapter.quote(symbol))
            except Exception:
                continue
        ladder.sort(key=lambda q: q.get("ask", float("inf")))
        return ladder

    def best_quote(self, symbol: str, side: str) -> Optional[Quote]:
        quotes = self.quotes(symbol)
        if not quotes:
            return None
        side = side.lower()
        if side.startswith("buy"):
            return min(quotes, key=lambda q: q.get("ask", float("inf")))
        return max(quotes, key=lambda q: q.get("bid", 0.0))

    # ------------------------------------------------------------------
    def effective_fill(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        side = side.lower()
        quotes = self.quotes(symbol)
        if not quotes:
            raise RuntimeError("no venue quotes available")

        key = (lambda q: q.get("ask", float("inf"))) if side.startswith("buy") else (lambda q: -q.get("bid", 0.0))
        quotes.sort(key=key)

        remaining = quantity
        notional = 0.0
        ladder: List[Tuple[str, float, float]] = []
        for quote in quotes:
            size = quote.get("ask_size" if side.startswith("buy") else "bid_size", 0.0)
            if size <= 0:
                continue
            take = min(size, remaining)
            if take <= 0:
                continue
            price = quote.get("ask" if side.startswith("buy") else "bid", 0.0)
            notional += take * price
            ladder.append((quote.get("venue", "?"), round(take, 6), round(price, 2)))
            remaining -= take
            if remaining <= 1e-6:
                break

        filled = quantity - max(0.0, remaining)
        if filled <= 0:
            raise RuntimeError("requested quantity could not be matched")
        avg_price = notional / filled

        first = quotes[0]
        bid = first.get("bid", 0.0)
        ask = first.get("ask", 0.0)
        mid = (bid + ask) / 2.0 if (bid and ask) else 0.0
        spread_bps = ((ask - bid) / mid * 1e4) if mid else 0.0

        edge_bps = 0.0
        if len(quotes) > 1:
            best_price = first.get("ask" if side.startswith("buy") else "bid", 0.0)
            comp_price = quotes[1].get("ask" if side.startswith("buy") else "bid", 0.0)
            ref = comp_price or 1.0
            edge_bps = (comp_price - best_price) / ref * 1e4 if ref else 0.0

        return {
            "symbol": symbol,
            "side": side,
            "avg_price": round(avg_price, 2),
            "filled": round(filled, 6),
            "remaining": round(max(0.0, remaining), 6),
            "ladder": ladder,
            "spread_bps": round(spread_bps, 2),
            "edge_bps": round(edge_bps, 2),
        }

    def submit(self, order: Order) -> Ack:
        venue = order.get("venue")
        adapter = self._adapters.get(venue) if venue else None
        if adapter is None:
            return {"venue": venue or "?", "accepted": False, "message": "unknown venue"}
        try:
            return adapter.submit_order(order)
        except Exception as exc:
            return {"venue": venue, "accepted": False, "message": str(exc)}


__all__ = ["EffectivePriceRouter", "VenueAdapter", "Quote", "Order", "Ack"]
