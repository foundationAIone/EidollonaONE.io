"""Minimal event-driven backtest engine (SE41 v4.1+ aligned).

Enhancements:
  * Optional SE41 context assembly for richer signal scoring
  * Ethos gating for signal leverage (deny/hold neutralization)
  * Latency & processed counts in metrics
  * Modular handler methods (_on_signal/_on_order/_on_fill)
  * Deterministic fallbacks keep module runnable without SE41 libs
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Deque, Optional, Any
from collections import deque
from time import time, perf_counter

# ─────────────────────────────────────────────────────────────────────────────
# SE41 imports (soft) – safe fallbacks
# ─────────────────────────────────────────────────────────────────────────────
try:  # Core numeric + ethos gate + signals
    from trading.helpers.se41_trading_gate import (  # type: ignore
        se41_numeric,
        ethos_decision,
        se41_signals,
    )
except Exception:  # pragma: no cover

    def se41_numeric(**_kw):  # type: ignore
        return {"score": 0.55}

    def ethos_decision(_tx: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        return {"decision": "allow"}

    def se41_signals(_ctx: Dict[str, Any]) -> Dict[str, float]:  # type: ignore
        return {"coherence": 0.55, "impetus": 0.3, "risk": 0.2}


try:  # Context builder (optional)
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    def assemble_se41_context(**kw):  # type: ignore
        return {
            "perception": kw.get("perception", {}),
            "intent": kw.get("intent", {}),
            "mirror": kw.get("mirror", {}),
            "substrate": kw.get("substrate", {"S_EM": 0.83}),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Event model
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Event:
    ts: float
    type: str


@dataclass(frozen=True)
class MarketEvent(Event):
    symbol: str
    price: float
    volume: float


@dataclass(frozen=True)
class SignalEvent(Event):
    symbol: str
    direction: int  # +1 long, -1 short


@dataclass(frozen=True)
class OrderEvent(Event):
    symbol: str
    direction: int
    qty: float


@dataclass(frozen=True)
class FillEvent(Event):
    symbol: str
    direction: int
    qty: float
    price: float


class EventDrivenEngine:
    """Tiny event-driven backtest loop with SE41 numeric screening and ethos gating."""

    def __init__(self) -> None:
        self.queue: Deque[Event] = deque()
        self.positions: Dict[str, float] = {}
        self.cash: float = 0.0
        self.pnl: float = 0.0
        self.metrics: Dict[str, float | int] = {
            "fills": 0,
            "orders": 0,
            "holds": 0,
            "denies": 0,
            "processed": 0,
            "latency_ms": 0.0,
        }

    # API -----------------------------------------------------------------
    def push(self, ev: Event) -> None:
        self.queue.append(ev)

    def process(
        self,
        max_events: Optional[int] = None,
        ctx_seed: Optional[Dict[str, Any]] = None,
        price_lookup: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        start = perf_counter()
        processed = 0
        if ctx_seed is None:
            ctx_seed = {
                "perception": {"market": "sim"},
                "intent": {"op": "event_loop"},
                "mirror": {"consistency": 0.71},
                "substrate": {"S_EM": 0.84},
            }
        ctx = assemble_se41_context(**ctx_seed)

        while self.queue:
            if max_events is not None and processed >= max_events:
                break
            ev = self.queue.popleft()
            if isinstance(ev, SignalEvent):
                self._on_signal(ev, ctx)
            elif isinstance(ev, OrderEvent):
                self._on_order(ev, price_lookup)
            elif isinstance(ev, FillEvent):
                self._on_fill(ev)
            processed += 1

        self.metrics["processed"] = processed
        self.metrics["latency_ms"] = round((perf_counter() - start) * 1000.0, 3)
        return {
            "positions": dict(self.positions),
            "pnl": float(self.pnl),
            "cash": float(self.cash),
            "metrics": dict(self.metrics),
        }

    # Internals -----------------------------------------------------------
    def _on_signal(self, ev: SignalEvent, ctx: Dict[str, Any]) -> None:
        lev = abs(ev.direction)
        numeric = se41_numeric(M_t=0.6, DNA_states=[1.0, lev, 1.0, 1.09])
        score = float(numeric.get("score", 0.55))
        # (Optional) richer path: score = se41_signals(ctx).get("coherence", score)
        gate = ethos_decision({"scope": "signal", "lev": lev, "score": score})
        decision = gate.get("decision", "allow") if isinstance(gate, dict) else "allow"
        if decision == "deny":
            self.metrics["denies"] += 1
            return
        if decision == "hold":
            self.metrics["holds"] += 1
            return
        self.push(OrderEvent(time(), "ORDER", ev.symbol, ev.direction, 1.0))

    def _on_order(
        self, ev: OrderEvent, price_lookup: Optional[Dict[str, float]]
    ) -> None:
        self.metrics["orders"] += 1
        px = 1.0 if price_lookup is None else float(price_lookup.get(ev.symbol, 1.0))
        self.push(FillEvent(time(), "FILL", ev.symbol, ev.direction, ev.qty, price=px))

    def _on_fill(self, ev: FillEvent) -> None:
        self.metrics["fills"] += 1
        self.positions[ev.symbol] = (
            self.positions.get(ev.symbol, 0.0) + ev.direction * ev.qty
        )
        cash_delta = -ev.direction * ev.qty * ev.price
        self.cash += cash_delta
        self.pnl += cash_delta


__all__ = [
    "EventDrivenEngine",
    "Event",
    "MarketEvent",
    "SignalEvent",
    "OrderEvent",
    "FillEvent",
]
