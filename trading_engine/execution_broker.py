# trading_engine/execution_broker.py
# ===================================================================
# EidollonaONE Execution Broker — SE41 v4.1+ aligned
#
# What this module does
# - Pre-trade checks: portfolio/risk limits, v4.1 symbolic coherence,
#   ethos gating for large/sensitive orders.
# - Venue routing: picks a venue by liquidity/urgency/coherence.
# - Execution: simulates partial fills, slippage, fees; produces an
#   auditable ExecutionReport and journals every fill.
# - Pluggable connectors: drop in real APIs per venue.
#
# Dependencies (first-party):
#   trading.helpers.se41_trading_gate: se41_signals, ethos_decision
#   symbolic_core.symbolic_equation41 & se41_context (fallback only)
# ===================================================================

from __future__ import annotations

import logging
import math
import random
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple

# v4.1 primitives (fallback only, main path uses se41_signals())
from symbolic_core.symbolic_equation41 import SymbolicEquation41
from symbolic_core.se41_context import assemble_se41_context

# Shared SE41 helpers (single source of truth — NO risky in-file injections)
from trading.helpers.se41_trading_gate import se41_signals, ethos_decision


# --------------------------- Domain models / enums ---------------------------


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class TimeInForce(Enum):
    DAY = "day"
    IOC = "ioc"
    FOK = "fok"
    GTC = "gtc"


class SymbolClass(Enum):
    EQUITY = "equity"
    FOREX = "forex"
    CRYPTO = "crypto"
    FUTURE = "future"
    OPTION = "option"
    OTHER = "other"


class ExecutionVenue(Enum):
    # Illustrative venues; map your connectors here
    NYSE = "nyse"
    NASDAQ = "nasdaq"
    CME = "cme"
    FX_LP1 = "fx_lp1"
    FX_LP2 = "fx_lp2"
    CRYPTO_CEX = "crypto_cex"
    CRYPTO_DEX = "crypto_dex"
    DARK = "dark"


@dataclass
class Order:
    order_id: str
    symbol: str
    side: Side
    qty: float
    order_type: OrderType = OrderType.MARKET
    tif: TimeInForce = TimeInForce.DAY
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    urgency: float = 0.5  # 0..1
    tags: List[str] = field(default_factory=list)  # ["sensitive", "client_x", ...]
    submitted_at: datetime = field(default_factory=datetime.now)
    client_id: Optional[str] = None


@dataclass
class Fill:
    fill_id: str
    order_id: str
    venue: ExecutionVenue
    price: float
    qty: float
    fee: float
    ts: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionReport:
    exec_id: str
    order_id: str
    status: str  # "filled" | "partial" | "rejected" | "cancelled"
    symbol: str
    side: Side
    avg_price: float
    filled_qty: float
    remaining_qty: float
    route: ExecutionVenue
    route_path: List[ExecutionVenue]
    fees_total: float
    fills: List[Fill]
    symbolic_coherence: float
    ethos_decision: str
    ethos_reason: str
    ts: datetime = field(default_factory=datetime.now)


@dataclass
class BrokerConfig:
    data_dir: Path = Path("execution_broker_data")
    # policy knobs
    max_notional_per_order: float = 2_000_000.0
    max_qty_per_order: float = 1_000_000.0
    daily_notional_cap: float = 50_000_000.0
    large_order_threshold: float = 250_000.0  # triggers ethos gating
    max_slippage_bps_market: float = 35.0
    max_slippage_bps_limit: float = 15.0
    # venue weights (routing)
    venue_liquidity: Dict[ExecutionVenue, float] = field(
        default_factory=lambda: {
            ExecutionVenue.NYSE: 1.0,
            ExecutionVenue.NASDAQ: 1.0,
            ExecutionVenue.CME: 0.9,
            ExecutionVenue.FX_LP1: 0.9,
            ExecutionVenue.FX_LP2: 0.85,
            ExecutionVenue.CRYPTO_CEX: 0.8,
            ExecutionVenue.CRYPTO_DEX: 0.6,
            ExecutionVenue.DARK: 0.4,
        }
    )


# --------------------------- v4.1 signal math helpers ---------------------------


def _min_ethos(sig: Dict[str, Any]) -> float:
    e = sig.get("ethos", {})
    if not isinstance(e, dict) or not e:
        return 0.0
    return min(
        float(e.get("authenticity", 0.0)),
        float(e.get("integrity", 0.0)),
        float(e.get("responsibility", 0.0)),
        float(e.get("enrichment", 0.0)),
    )


def _symbolic_coherence(sig: Dict[str, Any]) -> float:
    """
    Conservative, bounded coherence scalar [0..1] used for routing/execution risk.
    """
    if not sig:
        return 0.0
    coh = float(sig.get("coherence", 0.0))
    mc = float(sig.get("mirror_consistency", 0.0))
    me = _min_ethos(sig)
    risk = float(sig.get("risk", 0.2))
    unc = float(sig.get("uncertainty", 0.2))
    raw = 0.55 * coh + 0.25 * mc + 0.20 * me
    damp = max(0.35, 1.0 - 0.50 * (risk + unc))
    return max(0.0, min(1.0, raw * damp))


# --------------------------- Venue connector (stub) ---------------------------


class VenueConnector:
    """
    Pluggable venue connector interface.
    Implement real APIs per venue (send, cancel, replace, quotes).
    """

    def __init__(self, venue: ExecutionVenue) -> None:
        self.venue = venue
        self.logger = logging.getLogger(f"{__name__}.VenueConnector[{venue.value}]")

    def estimate_slippage_bps(self, symbol: str, qty: float, urgency: float) -> float:
        base = {
            ExecutionVenue.NYSE: 8,
            ExecutionVenue.NASDAQ: 8,
            ExecutionVenue.CME: 10,
            ExecutionVenue.FX_LP1: 5,
            ExecutionVenue.FX_LP2: 7,
            ExecutionVenue.CRYPTO_CEX: 12,
            ExecutionVenue.CRYPTO_DEX: 24,
            ExecutionVenue.DARK: 20,
        }[self.venue]
        size_penalty = min(60.0, math.log10(max(1.0, qty)) * 3.0)
        return (base + size_penalty) * (0.6 + urgency)

    def estimate_fee(self, notional: float) -> float:
        bps = {
            ExecutionVenue.NYSE: 0.5,
            ExecutionVenue.NASDAQ: 0.5,
            ExecutionVenue.CME: 0.6,
            ExecutionVenue.FX_LP1: 0.3,
            ExecutionVenue.FX_LP2: 0.35,
            ExecutionVenue.CRYPTO_CEX: 1.0,
            ExecutionVenue.CRYPTO_DEX: 1.4,
            ExecutionVenue.DARK: 0.7,
        }[self.venue]
        return round(notional * (bps / 10_000.0), 6)

    def market_execute(
        self, symbol: str, side: Side, qty: float, px_ref: float, urgency: float
    ) -> List[Tuple[float, float, float]]:
        """
        Returns a list of partial fills: [(price, qty, fee), ...]
        """
        # Simulate partials by venue liquidity
        parts = (
            1
            if self.venue
            in {ExecutionVenue.NYSE, ExecutionVenue.NASDAQ, ExecutionVenue.CRYPTO_CEX}
            else 2
        )
        remaining = qty
        fills: List[Tuple[float, float, float]] = []
        for i in range(parts):
            slice_qty = remaining if i == parts - 1 else round(qty / parts, 4)
            slp_bps = self.estimate_slippage_bps(symbol, slice_qty, urgency)
            # side-aware slippage
            px = px_ref * (
                1.0 + (slp_bps / 10_000.0) * (+1 if side == Side.BUY else -1)
            )
            fee = self.estimate_fee(px * slice_qty)
            fills.append((round(px, 6), slice_qty, fee))
            remaining -= slice_qty
        return fills


# --------------------------- Execution Broker ---------------------------


class ExecutionBroker:
    """
    v4.1 Execution Broker
    - Pre-trade: policy + v4.1 + ethos gate
    - Route: pick a venue by liquidity & coherence
    - Execute: simulate fills & fees, record audit
    """

    def __init__(self, config: Optional[BrokerConfig] = None) -> None:
        self.logger = logging.getLogger(f"{__name__}.ExecutionBroker")
        self.config = config or BrokerConfig()
        self.config.data_dir.mkdir(exist_ok=True)
        self._se41 = SymbolicEquation41()  # fallback only

        # Wire basic venue connectors (swap for real ones)
        self.venues: Dict[ExecutionVenue, VenueConnector] = {
            v: VenueConnector(v) for v in ExecutionVenue
        }

        # Simple daily counters (reset out of scope)
        self._daily_notional = 0.0

    # ---------- Public API ----------

    def execute(
        self, order: Order, px_ref: float, portfolio_cash: float
    ) -> ExecutionReport:
        """
        Full life-cycle execution: checks → route → fills → report → journal.
        """
        # 1) Signals & coherence
        sig = self._signals()
        coh = _symbolic_coherence(sig)

        # 2) Pre-trade checks & ethos gating
        self._policy_checks(order, px_ref, portfolio_cash)
        decision, reason = self._ethos_gate(order, px_ref)

        if decision != "allow":
            return self._reject(order, "ethos_denied", coh, decision, reason)

        # 3) Route
        venue = self._route(order, coh)
        connector = self.venues[venue]

        # 4) Execute (market path; extend for limit/stop)
        fills_raw = connector.market_execute(
            order.symbol, order.side, order.qty, px_ref, order.urgency
        )
        fills: List[Fill] = []
        notional = 0.0
        total_fee = 0.0
        filled_qty = 0.0

        for px, q, fee in fills_raw:
            filled_qty += q
            notional += px * q
            total_fee += fee
            fills.append(
                Fill(
                    fill_id=f"fill_{uuid.uuid4().hex[:8]}",
                    order_id=order.order_id,
                    venue=venue,
                    price=px,
                    qty=q,
                    fee=fee,
                )
            )

        avg_price = (
            round(notional / max(1e-9, filled_qty), 6) if filled_qty > 0 else 0.0
        )
        remaining = max(0.0, order.qty - filled_qty)
        status = (
            "filled"
            if remaining == 0
            else ("partial" if filled_qty > 0 else "rejected")
        )

        report = ExecutionReport(
            exec_id=f"exec_{uuid.uuid4().hex[:8]}",
            order_id=order.order_id,
            status=status,
            symbol=order.symbol,
            side=order.side,
            avg_price=avg_price,
            filled_qty=round(filled_qty, 6),
            remaining_qty=round(remaining, 6),
            route=venue,
            route_path=[venue],
            fees_total=round(total_fee, 6),
            fills=fills,
            symbolic_coherence=round(coh, 4),
            ethos_decision=decision,
            ethos_reason=reason,
        )

        # 5) Update counters & journal
        self._daily_notional += notional
        self._journal(report, order, px_ref, portfolio_cash, sig)

        return report

    # ---------- Helpers ----------

    def _signals(self) -> Dict[str, Any]:
        sig = se41_signals()
        if sig:
            return sig
        try:
            s = self._se41.evaluate(assemble_se41_context())
            return getattr(s, "__dict__", {}) if hasattr(s, "__dict__") else {}
        except Exception:
            # guarded fallback
            return {
                "coherence": 0.65,
                "mirror_consistency": 0.6,
                "risk": 0.25,
                "uncertainty": 0.25,
                "ethos": {
                    "authenticity": 0.9,
                    "integrity": 0.9,
                    "responsibility": 0.9,
                    "enrichment": 0.9,
                },
            }

    def _policy_checks(self, order: Order, px_ref: float, cash: float) -> None:
        """
        Simple, local policy gates (replace with your risk/compliance systems).
        """
        notional = order.qty * px_ref
        if order.qty <= 0 or px_ref <= 0:
            raise ValueError("Invalid order quantity or price reference.")
        if notional > self.config.max_notional_per_order:
            raise ValueError("Order notional exceeds per-order limit.")
        if order.qty > self.config.max_qty_per_order:
            raise ValueError("Order quantity exceeds per-order limit.")
        if self._daily_notional + notional > self.config.daily_notional_cap:
            raise ValueError("Daily notional cap reached.")
        # cash check for buy / simplistic
        if order.side == Side.BUY and cash < notional:
            raise ValueError("Insufficient cash for BUY order.")

    def _ethos_gate(self, order: Order, px_ref: float) -> Tuple[str, str]:
        """
        Four Pillars gate for large or sensitive orders.
        """
        notional = order.qty * px_ref
        if notional >= self.config.large_order_threshold or "sensitive" in order.tags:
            tx = {
                "id": f"ord_{order.order_id}",
                "purpose": "execution",
                "amount": float(notional),
                "currency": "NOM",
                "tags": list(order.tags),
            }
            return ethos_decision(tx)
        return "allow", "below_threshold"

    def _route(self, order: Order, coherence: float) -> ExecutionVenue:
        """
        Liquidity-weighted + coherence boost routing.
        """
        weights = dict(self.config.venue_liquidity)
        # Simple coherence bump for lit venues; reduce dark if low coherence
        if coherence >= 0.7:
            weights[ExecutionVenue.NYSE] *= 1.1
            weights[ExecutionVenue.NASDAQ] *= 1.1
        else:
            weights[ExecutionVenue.DARK] *= 0.9

        # urgency nudges
        if order.urgency > 0.7:
            weights[ExecutionVenue.CRYPTO_CEX] *= 1.05
            weights[ExecutionVenue.FX_LP1] *= 1.05

        # pick by normalized probabilities
        total = sum(weights.values())
        r = random.random() * total
        acc = 0.0
        for v, w in weights.items():
            acc += w
            if r <= acc:
                return v
        return ExecutionVenue.NYSE

    def _reject(
        self,
        order: Order,
        reason: str,
        coherence: float,
        decision: str,
        ethos_reason: str,
    ) -> ExecutionReport:
        return ExecutionReport(
            exec_id=f"exec_{uuid.uuid4().hex[:8]}",
            order_id=order.order_id,
            status="rejected",
            symbol=order.symbol,
            side=order.side,
            avg_price=0.0,
            filled_qty=0.0,
            remaining_qty=order.qty,
            route=ExecutionVenue.DARK,
            route_path=[ExecutionVenue.DARK],
            fees_total=0.0,
            fills=[],
            symbolic_coherence=round(coherence, 4),
            ethos_decision=decision,
            ethos_reason=f"{ethos_reason}:{reason}",
        )

    def _journal(
        self,
        report: ExecutionReport,
        order: Order,
        px_ref: float,
        cash: float,
        sig: Dict[str, Any],
    ) -> None:
        """
        Append JSONL line with execution details + inputs.
        """
        try:
            import json

            p = self.config.data_dir / "execution_journal.jsonl"
            row = {
                "ts": report.ts.isoformat(),
                "exec": asdict(report),
                "order": {
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "qty": order.qty,
                    "type": order.order_type.value,
                    "tif": order.tif.value,
                    "limit_price": order.limit_price,
                    "urgency": order.urgency,
                    "tags": order.tags,
                },
                "px_ref": px_ref,
                "portfolio_cash": cash,
                "signals": sig,
            }
            with p.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.warning("Execution journal append failed: %s", e)


# --------------------------- Factory & demo ---------------------------


def create_execution_broker(**kwargs) -> ExecutionBroker:
    return ExecutionBroker(BrokerConfig(**kwargs) if kwargs else None)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 72)
    print("EidollonaONE Execution Broker v4.1+  —  ethical, coherent, auditable")
    print("=" * 72)

    try:
        broker = create_execution_broker()
        # demo order
        ord1 = Order(
            order_id=f"ord_{uuid.uuid4().hex[:8]}",
            symbol="AAPL",
            side=Side.BUY,
            qty=12_500,
            order_type=OrderType.MARKET,
            tif=TimeInForce.IOC,
            urgency=0.75,
            tags=["equity"],
        )
        px_ref = 198.25
        cash = 5_000_000.0
        rep = broker.execute(ord1, px_ref, cash)
        print(
            f"status={rep.status} venue={rep.route.value} avg={rep.avg_price} "
            f"filled={rep.filled_qty}/{rep.remaining_qty+rep.filled_qty} "
            f"coh={rep.symbolic_coherence} ethos={rep.ethos_decision}:{rep.ethos_reason}"
        )
    except Exception as e:
        print(f"❌ Broker demo failed: {e}")
