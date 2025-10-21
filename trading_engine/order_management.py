"""trading_engine/order_management.py
===================================================================
EidollonaONE Order Management System — SE41 v4.1+ aligned

What this module does
- Validates every order against SE41Signals + Ethos (no unsafe flow).
- Optimizes order type/price/priority symbolically (coherence-aware).
- Routes orders with a quantum-aware venue scorer (speed/liquidity/cost).
- Journals each decision to JSONL for auditability.
- Provides async submit/cancel APIs and live flow metrics.
===================================================================
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Optional compatibility with a higher-level engine export
try:
    from trading_engine import TradingEngine  # noqa: F401

    __all__ = ["TradingEngine"]
except Exception:
    __all__ = []

# ---- SE41 v4.1 unified imports ------------------------------------
from symbolic_core.symbolic_equation41 import SymbolicEquation41
from symbolic_core.context_builder import assemble_se41_context
from trading.helpers.se41_trading_gate import (
    se41_signals,  # returns last SE41 signals packet
    ethos_decision,  # returns ("allow"/"hold"/"deny", reason)
    se41_numeric,  # bounded numeric synthesis for local decisions
)

# ---- enum types (single canonical source) -------------------------
# Removed incorrect TradeType import; define local Side for BUY/SELL


class ExecutionStrategy(Enum):
    MARKET = "market"
    LIMIT = "limit"


class ExecutionStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    WORKING = "working"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


# --------------------------- enums & dataclasses ---------------------------


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    ICEBERG = "iceberg"
    BRACKET = "bracket"
    OCO = "oco"  # one-cancels-other
    SYMBOLIC_ADAPTIVE = "symbolic_adaptive"  # auto-tunes type/price


class OrderPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    DEFERRED = 5


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderState(Enum):
    CREATED = "created"
    VALIDATED = "validated"
    QUEUED = "queued"
    SUBMITTED = "submitted"
    WORKING = "working"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Order:
    """Enhanced order with symbolic validation/coherence and journaling fields."""

    order_id: str
    symbol: str
    order_type: OrderType
    trade_type: Side
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    trail_amount: Optional[float] = None
    time_in_force: str = "DAY"

    # Order state
    state: OrderState = OrderState.CREATED
    priority: OrderPriority = OrderPriority.NORMAL
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    average_fill_price: float = 0.0

    # Timestamps
    created_time: datetime = field(default_factory=datetime.now)
    submitted_time: Optional[datetime] = None
    last_update: datetime = field(default_factory=datetime.now)
    expiry_time: Optional[datetime] = None

    # Enhanced tracking
    fees: float = 0.0
    slippage: float = 0.0
    execution_venues: List[str] = field(default_factory=list)

    # Symbolic validation
    symbolic_coherence: float = 0.0
    quantum_probability: float = 0.0
    consciousness_alignment: float = 0.0
    validation_score: float = 0.0

    # Parent/child for complex orders
    parent_order_id: Optional[str] = None
    child_order_ids: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.remaining_quantity == 0.0:
            self.remaining_quantity = float(self.quantity)


@dataclass
class OrderFlow:
    """Lightweight live metrics for dashboards and health checks."""

    total_orders: int = 0
    active_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    rejected_orders: int = 0
    total_volume: float = 0.0
    average_order_size: float = 0.0
    fill_rate: float = 0.0
    cancellation_rate: float = 0.0
    symbolic_coherence_avg: float = 0.0
    quantum_optimization_score: float = 0.0
    execution_quality_score: float = 0.0


# --------------------------- symbolic optimizer ---------------------------


class SymbolicOrderOptimizer:
    """Symbolic equation-based order optimization (type/price/priority/venue bias)."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SymbolicOrderOptimizer")
        self._se41 = SymbolicEquation41()

    def optimize_order_parameters(
        self,
        order: Order,
        market_conditions: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Use SE41 numeric synthesis to choose order type, price improvement, venue bias,
        and priority tweak based on volatility/liquidity/spread/urgency/time pressure.
        """
        try:
            vol = float(market_conditions.get("volatility", 0.2))
            liq = float(market_conditions.get("liquidity", 0.7))
            spr = float(market_conditions.get("spread", 0.01))  # absolute price gap
            mom = float(market_conditions.get("momentum", 0.0))
            depth = float(market_conditions.get("depth", 0.5))

            order_size_factor = min(order.quantity / 10000.0, 1.0)
            urgency_factor = 1.0 / float(order.priority.value)  # critical → 1.0
            time_factor = self._time_factor(order)

            # SE41 bounded numeric synthesis (robust to noise)
            numeric = se41_numeric(
                M_t=max(0.05, min(liq, 1.0)),  # use liquidity as the modulation source
                DNA_states=[
                    1.0,
                    vol,
                    liq,
                    min(spr, 0.1),
                    mom,
                    depth,
                    order_size_factor,
                    urgency_factor,
                    time_factor,
                    1.05,
                ],
                harmonic_patterns=[
                    1.0,
                    1.1,
                    max(0.0, 1.0 - min(vol, 1.0)),
                    min(liq, 1.0),
                    max(0.0, 1.0 - min(spr * 100.0, 1.0)),
                    min(depth, 1.0),
                    0.95,
                ],
            )

            is_valid = (
                isinstance(numeric, (int, float))
                and math.isfinite(numeric)
                and 0.001 < abs(numeric) < 1000.0
            )
            if not is_valid:
                return {"valid": False, "optimization_score": 0.0}

            score = min(abs(float(numeric)) / 60.0, 1.0)
            order.symbolic_coherence = score

            params = self._build_optimized_params(order, score, vol, liq, spr, depth)
            self.logger.info(
                f"[SE41] order optimization {order.symbol} score={score:.3f}"
            )

            return {
                "valid": True,
                "optimization_score": score,
                "symbolic_result": numeric,
                "optimized_parameters": params,
                "recommended_order_type": params.get("order_type"),
                "priority_adjustment": params.get("priority_adjustment", 0),
                "optimization_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Order optimization failed: {e}")
            return {"valid": False, "optimization_score": 0.0, "error": str(e)}

    def _time_factor(self, order: Order) -> float:
        try:
            if order.expiry_time:
                ttl = (order.expiry_time - datetime.now()).total_seconds()
                return max(0.05, min(ttl / 86400.0, 1.0))
            return 0.8  # DAY default
        except Exception:
            return 0.5

    def _build_optimized_params(
        self,
        order: Order,
        score: float,
        vol: float,
        liq: float,
        spr: float,
        depth: float,
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {}

        # Choose order type with coherence & market context
        if score >= 0.8:
            if vol <= 0.15 and liq >= 0.8:
                out["order_type"] = OrderType.SYMBOLIC_ADAPTIVE
            elif spr <= 0.005:
                out["order_type"] = OrderType.MARKET
            else:
                out["order_type"] = OrderType.LIMIT
        elif score >= 0.6:
            if vol >= 0.3:
                out["order_type"] = OrderType.STOP_LIMIT
            elif order.quantity > 5000:
                out["order_type"] = OrderType.ICEBERG
            else:
                out["order_type"] = OrderType.LIMIT
        else:
            out["order_type"] = OrderType.MARKET

        # Priority tweak: higher coherence → raise priority
        if score >= 0.9:
            out["priority_adjustment"] = -1
        elif score <= 0.3:
            out["priority_adjustment"] = 1

        # Price improvement target for limit / stop-limit
        if (
            out["order_type"]
            in (OrderType.LIMIT, OrderType.STOP_LIMIT, OrderType.SYMBOLIC_ADAPTIVE)
            and order.price
        ):
            bp = max(spr / max(order.price, 1e-9), 0.0)
            improvement = score * bp * 0.5
            if order.trade_type == Side.BUY:
                out["optimized_price"] = order.price * (1 - improvement)
            else:
                out["optimized_price"] = order.price * (1 + improvement)

        # Venue preference hint (the router will consider it with other signals)
        if score >= 0.7 and liq >= 0.7:
            out["preferred_venue"] = "primary_exchange"
        elif liq >= 0.6:
            out["preferred_venue"] = "dark_pool"
        else:
            out["preferred_venue"] = "electronic_network"

        return out


# --------------------------- quantum router ---------------------------


class QuantumOrderRouter:
    """Quantum-aware venue scoring + light slicing guidance."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.QuantumOrderRouter")
        self.routing_history = deque(maxlen=1000)

    def route_order(
        self, order: Order, market_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            venues = [
                "primary_exchange",
                "dark_pool_1",
                "dark_pool_2",
                "electronic_network_1",
                "electronic_network_2",
                "alternative_trading_system",
            ]

            quantum = random.uniform(0.9, 1.1)
            coh = float(getattr(order, "symbolic_coherence", 0.5))

            scores = {
                v: self._score_venue(v, order, market_conditions, quantum, coh)
                for v in venues
            }
            best = max(scores, key=lambda k: scores[k])

            params = self._routing_params(order, best, scores[best], market_conditions)
            self.routing_history.append(
                {
                    "order_id": order.order_id,
                    "venue": best,
                    "score": scores[best],
                    "quantum": quantum,
                    "ts": datetime.now().isoformat(),
                }
            )

            self.logger.info(
                f"[Route] {order.order_id} → {best} (score={scores[best]:.3f})"
            )
            return {
                "optimal_venue": best,
                "venue_score": scores[best],
                "venue_scores": scores,
                "routing_parameters": params,
                "quantum_enhancement": quantum,
                "expected_fill_time": params.get("expected_fill_time"),
                "routing_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Order routing failed: {e}")
            return {"optimal_venue": "primary_exchange", "venue_score": 0.5}

    def _score_venue(
        self, venue: str, order: Order, mc: Dict[str, Any], q: float, c: float
    ) -> float:
        chars = {
            "primary_exchange": {"liquidity": 0.9, "speed": 0.7, "cost": 0.6},
            "dark_pool_1": {"liquidity": 0.7, "speed": 0.5, "cost": 0.8},
            "dark_pool_2": {"liquidity": 0.6, "speed": 0.6, "cost": 0.9},
            "electronic_network_1": {"liquidity": 0.8, "speed": 0.9, "cost": 0.7},
            "electronic_network_2": {"liquidity": 0.7, "speed": 0.8, "cost": 0.8},
            "alternative_trading_system": {"liquidity": 0.5, "speed": 0.6, "cost": 0.9},
        }
        ch = dict(chars.get(venue, {"liquidity": 0.5, "speed": 0.5, "cost": 0.5}))

        if order.quantity > 10000 and "dark_pool" in venue:
            ch["liquidity"] *= 1.15
        vol = float(mc.get("volatility", 0.2))
        if vol > 0.3:
            ch["speed"] *= 1.2

        # composite + quantum/coherence blend
        base = ch["liquidity"] * 0.45 + ch["speed"] * 0.35 + ch["cost"] * 0.20
        return min(max(base * q * (0.5 + 0.5 * c), 0.0), 1.0)

    def _routing_params(
        self, order: Order, venue: str, vscore: float, mc: Dict[str, Any]
    ) -> Dict[str, Any]:
        base_fill = {
            "primary_exchange": 5,
            "dark_pool_1": 30,
            "dark_pool_2": 45,
            "electronic_network_1": 10,
            "electronic_network_2": 15,
            "alternative_trading_system": 60,
        }.get(venue, 30)

        size_factor = min(order.quantity / 1000.0, 5.0)
        vol = float(mc.get("volatility", 0.2))
        liq = float(mc.get("liquidity", 0.7))
        cond = 1.0 + vol * 0.5 - liq * 0.3

        fill_time = base_fill * (1 + size_factor * 0.2) * cond
        slice_size = (
            min(max(order.quantity * 0.1, 100.0), 2000.0)
            if order.quantity > 5000
            else order.quantity
        )

        return {
            "expected_fill_time": fill_time,
            "slice_size": slice_size,
            "max_participation_rate": 0.2,
            "price_improvement_target": vscore * 0.0005,
            "retry_attempts": 3,
            "timeout_seconds": max(15.0, fill_time * 3.0),
        }


# --------------------------- order management ---------------------------


class OrderManagementSystem:
    """
    Order Management System (SE41 v4.1+)
      • SE41 + Ethos validation (no unsafe/unethical flow).
      • Symbolic optimization → type/price/priority.
      • Quantum-aware routing → venue + slicing guide.
      • Journal decisions → JSONL.
    """

    def __init__(self, system_directory: Optional[str] = None):
        self.logger = logging.getLogger(f"{__name__}.OrderManagementSystem")

        # dirs/journal
        self.system_directory = Path(system_directory or "order_management_data")
        self.system_directory.mkdir(exist_ok=True)
        self._journal_path = self.system_directory / "oms_journal.jsonl"

        # subsystems
        self.optimizer = SymbolicOrderOptimizer()
        self.router = QuantumOrderRouter()

        # state
        self.orders: Dict[str, Order] = {}
        self.order_queue: deque[str] = deque()
        self.execution_queue: deque[str] = deque()
        self.order_flow = OrderFlow()

        # config
        self.max_orders_per_symbol = 20
        self.max_active_orders = 500
        self.order_timeout_default = 3600.0
        self.processing_interval = 1.0

        # runtime
        self.processing_active = True
        self._processing_task = None

        self.logger.info(
            "Order Management System v4.1+ initialized (symbolic✓ quantum✓ ethos✓)"
        )

    # ---- public API

    async def submit_order(
        self, order: Order, market_conditions: Dict[str, Any]
    ) -> str:
        """
        Validate → Optimize → Route → Queue.
        Ethos gating prevents unsafe order intents (e.g., manipulative bursts).
        """
        try:
            v = await self._validate_order(order, market_conditions)
            if not v.get("valid", False):
                order.state = OrderState.REJECTED
                self._journal(
                    {
                        "type": "reject",
                        "order": _order_dict(order),
                        "reason": v.get("reason", "validation_failed"),
                    }
                )
                self.logger.warning(
                    f"Order rejected: {v.get('reason', 'validation_failed')}"
                )
                return order.order_id

            # optimization
            opt = self.optimizer.optimize_order_parameters(order, market_conditions)
            if opt.get("valid", False):
                self._apply_optimizations(order, opt.get("optimized_parameters", {}))

            # routing
            route = self.router.route_order(order, market_conditions)
            order.execution_venues = [route.get("optimal_venue", "primary_exchange")]

            # update state
            order.state = OrderState.VALIDATED
            order.submitted_time = datetime.now()
            order.last_update = datetime.now()

            # default expiry for DAY
            if not order.expiry_time and order.time_in_force.upper() == "DAY":
                order.expiry_time = datetime.now() + timedelta(hours=16)

            self.orders[order.order_id] = order
            self.order_queue.append(order.order_id)

            # flow metrics
            self.order_flow.total_orders += 1
            self.order_flow.active_orders += 1
            self.order_flow.total_volume += order.quantity
            self.order_flow.average_order_size = self.order_flow.total_volume / max(
                self.order_flow.total_orders, 1
            )

            self._journal(
                {
                    "type": "submit",
                    "order": _order_dict(order),
                    "opt": opt,
                    "route": route,
                    "ts": datetime.now().isoformat(),
                }
            )

            self.logger.info(
                f"Submitted {order.symbol} {order.trade_type.value} "
                f"qty={order.quantity} type={order.order_type.value}"
            )
            return order.order_id

        except Exception as e:
            self.logger.error(f"Order submission failed: {e}")
            order.state = OrderState.REJECTED
            self._journal(
                {"type": "error_submit", "order": _order_dict(order), "error": str(e)}
            )
            return order.order_id

    async def cancel_order(self, order_id: str, reason: str = "user_request") -> bool:
        try:
            order = self.orders.get(order_id)
            if not order:
                return False
            if order.state in (
                OrderState.FILLED,
                OrderState.CANCELLED,
                OrderState.REJECTED,
                OrderState.EXPIRED,
            ):
                return False

            order.state = OrderState.CANCELLED
            order.last_update = datetime.now()
            self.order_flow.active_orders = max(0, self.order_flow.active_orders - 1)
            self.order_flow.cancelled_orders += 1

            self._journal(
                {
                    "type": "cancel",
                    "order_id": order_id,
                    "reason": reason,
                    "ts": datetime.now().isoformat(),
                }
            )
            self.logger.info(f"Cancelled {order_id} (reason={reason})")
            return True

        except Exception as e:
            self.logger.error(f"Order cancellation failed: {e}")
            self._journal(
                {"type": "error_cancel", "order_id": order_id, "error": str(e)}
            )
            return False

    # ---- validation / optimization helpers

    async def _validate_order(self, order: Order, mc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build SE41 context and Ethos-gate the intent.
        Rejects oversized MARKET orders in wide-spread/high-volatility scenarios,
        or any explicitly disallowed intents by Ethos.
        """
        try:
            signals: Dict[str, Any] = se41_signals() or {}
            # Build a minimal SE41 context using canonical hints
            _ = assemble_se41_context(
                coherence_hint=float(signals.get("coherence", 0.6)),
                risk_hint=float(signals.get("risk", 0.2)),
                uncertainty_hint=float(signals.get("uncertainty", 0.2)),
                mirror_consistency=float(signals.get("mirror_consistency", 0.5)),
                s_em=float(signals.get("S_EM", 0.8)),
            )

            # ethos gate (risk-raising)
            allow, why = ethos_decision(
                {
                    "id": order.order_id,
                    "purpose": "submit_order",
                    "amount": float(order.quantity),
                    "currency": "NOM",
                    "tags": ["order", order.order_type.value, order.trade_type.value],
                }
            )
            if allow == "deny":
                return {"valid": False, "reason": f"ethos_denied: {why}"}

            # numeric sanity
            vol = float(mc.get("volatility", 0.2))
            spr = float(mc.get("spread", 0.01))
            liq = float(mc.get("liquidity", 0.7))

            numeric = se41_numeric(
                M_t=signals.get("coherence", 0.5),
                DNA_states=[
                    1.0,
                    vol,
                    liq,
                    min(spr, 0.1),
                    (order.quantity / 10000.0),
                    1.1,
                ],
                harmonic_patterns=[
                    1.0,
                    1.1,
                    1.15,
                    float(signals.get("risk", 0.2)),
                    float(signals.get("uncertainty", 0.2)),
                ],
            )
            ok = isinstance(numeric, (int, float)) and math.isfinite(numeric)
            score = min(abs(float(numeric)) / 80.0, 1.0) if ok else 0.0

            order.validation_score = score
            order.symbolic_coherence = max(order.symbolic_coherence, score)

            # simple guardrails
            if (
                order.order_type == OrderType.MARKET
                and (vol > 0.5 or spr > 0.01)
                and order.quantity > 5000
            ):
                return {
                    "valid": False,
                    "reason": "market_order_excessive_in_wide_or_volatile",
                }

            if allow == "hold":
                return {"valid": False, "reason": f"ethos_hold: {why}"}

            return {
                "valid": score >= 0.25,
                "reason": "ok" if score >= 0.25 else "low_symbolic_score",
            }

        except Exception as e:
            return {"valid": False, "reason": f"validation_error: {e}"}

    def _apply_optimizations(self, order: Order, params: Dict[str, Any]) -> None:
        try:
            if "order_type" in params:
                order.order_type = params["order_type"]
            if "optimized_price" in params and order.price:
                order.price = float(params["optimized_price"])

            # priority shift
            adj = int(params.get("priority_adjustment", 0))
            if adj != 0:
                new_val = max(1, min(5, order.priority.value + adj))
                order.priority = OrderPriority(new_val)

            # preferred venue is advisory; stored in order.execution_venues at routing step
        except Exception:
            pass

    # ---- journaling

    def _journal(self, obj: Dict[str, Any]) -> None:
        try:
            with self._journal_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(obj, default=_json_default) + "\n")
        except Exception:
            pass


# --------------------------- utilities ---------------------------


def _json_default(o: Any):
    if isinstance(o, (datetime,)):
        return o.isoformat()
    if isinstance(o, Enum):
        return o.value
    return str(o)


def _order_dict(o: Order) -> Dict[str, Any]:
    return {
        "order_id": o.order_id,
        "symbol": o.symbol,
        "order_type": o.order_type.value,
        "trade_type": o.trade_type.value,
        "quantity": o.quantity,
        "price": o.price,
        "stop_price": o.stop_price,
        "trail_amount": o.trail_amount,
        "tif": o.time_in_force,
        "state": o.state.value,
        "priority": o.priority.value,
        "filled_qty": o.filled_quantity,
        "remaining_qty": o.remaining_quantity,
        "avg_fill_price": o.average_fill_price,
        "created_time": o.created_time.isoformat(),
        "submitted_time": o.submitted_time.isoformat() if o.submitted_time else None,
        "last_update": o.last_update.isoformat(),
        "expiry_time": o.expiry_time.isoformat() if o.expiry_time else None,
        "fees": o.fees,
        "slippage": o.slippage,
        "venues": o.execution_venues,
        "symbolic_coherence": o.symbolic_coherence,
        "quantum_probability": o.quantum_probability,
        "consciousness_alignment": o.consciousness_alignment,
        "validation_score": o.validation_score,
        "parent_order_id": o.parent_order_id,
        "child_order_ids": o.child_order_ids,
    }


# --------------------------- factory & smoke ---------------------------


def create_order_management_system(**kwargs) -> OrderManagementSystem:
    return OrderManagementSystem(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 70)
    print("EidollonaONE Order Management System v4.1+ — coherent • ethical • auditable")
    print("=" * 70)

    oms = create_order_management_system()
    # tiny smoke: create a limit order in moderate conditions
    test_order = Order(
        order_id=f"ord_{int(time.time())}",
        symbol="EIDO",
        order_type=OrderType.LIMIT,
        trade_type=Side.BUY,
        quantity=1200,
        price=100.00,
        time_in_force="DAY",
        priority=OrderPriority.NORMAL,
    )
    import asyncio

    asyncio.run(
        oms.submit_order(
            test_order,
            market_conditions={
                "volatility": 0.22,
                "liquidity": 0.75,
                "spread": 0.02,
                "momentum": 0.05,
                "depth": 0.6,
            },
        )
    )
    print("Submitted order; see order_management_data/oms_journal.jsonl")
