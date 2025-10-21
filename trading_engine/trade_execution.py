from __future__ import annotations

import asyncio
import logging
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, cast

# ---------------------------------------------------------------------------
# SE41 (v4.1+) unified interface
# ---------------------------------------------------------------------------
from symbolic_core.symbolic_equation import SymbolicEquation41
from trading.helpers.se41_trading_gate import (
    se41_signals,  # builds signals packet (coherence, risk, impetus, ethos, embodiment)
    ethos_decision_envelope,  # returns {decision: 'allow'|'hold'|'deny', pillars:{...}, reason:...}
    se41_numeric,  # bounded numeric synthesis for fast paths
)

"""
⚡ EidollonaONE Trade Execution Engine v4.1+

Advanced, ethically-gated execution:
  • Symbolic (SE41) optimization → strategy, timing, and priority
  • Ethos gate (A/I/R/E) at last mile: allow / hold / deny + reasons
  • Quantum timing enhancement with safe fallbacks
  • Execution quality telemetry (fill, slippage, symbolic alignment)

Default posture: SAFE; denies when signals/ethos are not satisfied.
"""

# Optional dependency on AI executor signal types (kept soft)
TRADE_EXECUTOR_AVAILABLE = False

if TYPE_CHECKING:  # pragma: no cover - static analysis only
    from trading_engine.ai_trade_executor import TradeType, TradingSignal
    TRADE_EXECUTOR_AVAILABLE = True
else:
    try:
        from trading_engine.ai_trade_executor import (
            TradeType,
            TradingSignal,
        )

        TRADE_EXECUTOR_AVAILABLE = True
    except Exception:
        TRADE_EXECUTOR_AVAILABLE = False

        class TradeType(Enum):
            BUY = "buy"
            SELL = "sell"

        # Minimal TradingSignal shim for smoke usage (only fields referenced here)
        @dataclass
        class TradingSignal:
            signal_id: str
            symbol: str
            trade_type: TradeType
            position_size: float
            entry_price: float
            market_type: str = "stocks"
            confidence: float = 0.6
            risk_level: str = "medium"
            target_price: float = 0.0
            stop_loss: float = 0.0
            reasoning: str = "fallback"
            symbolic_validation: float = 0.6
            quantum_probability: float = 0.5


# ---------------------------------------------------------------------------
# Execution enums and data structures
# ---------------------------------------------------------------------------
class ExecutionStrategy(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TWAP = "twap"  # Time Weighted Average Price
    VWAP = "vwap"  # Volume Weighted Average Price
    ICEBERG = "iceberg"
    SYMBOLIC_OPTIMAL = "symbolic_optimal"


class ExecutionStatus(Enum):
    PENDING = "pending"
    WORKING = "working"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ExecutionOrder:
    """Execution order with symbolic/quantum metadata."""

    order_id: str
    signal_id: str
    symbol: str
    trade_type: TradeType
    quantity: float
    price: Optional[float]
    strategy: ExecutionStrategy
    status: ExecutionStatus = ExecutionStatus.PENDING
    filled_quantity: float = 0.0
    average_price: float = 0.0
    fees: float = 0.0
    slippage: float = 0.0
    symbolic_coherence: float = 0.0
    quantum_probability: float = 0.0
    execution_priority: int = 5  # 1..10
    time_in_force: str = "DAY"
    created_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionMetrics:
    """Aggregated execution performance."""

    total_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    average_fill_time_ms: float = 0.0
    average_slippage: float = 0.0
    total_fees: float = 0.0
    execution_quality_score: float = 0.0
    symbolic_alignment_score: float = 0.0


# ---------------------------------------------------------------------------
# Symbolic optimizer: choose a strategy that matches signals & conditions
# ---------------------------------------------------------------------------
class SymbolicExecutionOptimizer:
    def __init__(self):
        self.log = logging.getLogger(f"{__name__}.SymbolicExecutionOptimizer")
        self._se41 = SymbolicEquation41()

    def optimize_execution_strategy(
        self, signal: Any, market: Dict[str, Any]
    ) -> ExecutionStrategy:
        """
        Choose an execution strategy with a bounded SE41 numeric.
        """
        try:
            vol = float(market.get("volatility", 0.2))
            liq = float(market.get("liquidity", 0.7))
            spr = float(market.get("spread", 0.01))
            volp = float(market.get("volume", 1_000_000))

            numeric = se41_numeric(
                M_t=max(0.05, (1.0 - min(vol, 1.0)) * 0.6 + min(liq, 1.0) * 0.4),
                DNA_states=[
                    1.0,
                    min(signal.confidence, 1.0),
                    max(0.0, 1.0 - min(spr * 100, 1.0)),  # tighter spread ↑
                    min(volp / 10_000_000.0, 1.0),
                    min(signal.symbolic_validation, 1.0),
                    1.05,
                ],
                harmonic_patterns=[
                    1.0,
                    1.1,
                    (1.0 - min(vol, 1.0)),
                    min(liq, 1.0),
                    max(0.0, 1.0 - min(spr * 100, 1.0)),
                    min(signal.quantum_probability, 1.0),
                    0.95,
                ],
            )
            ok = (
                isinstance(numeric, (int, float))
                and math.isfinite(numeric)
                and 0.001 < abs(numeric) < 1000.0
            )
            score = min(abs(float(numeric)) / 45.0, 1.0) if ok else 0.45

            # Strategy ladder (simple and robust)
            if score >= 0.8 and liq >= 0.7:
                if vol <= 0.15:
                    return ExecutionStrategy.SYMBOLIC_OPTIMAL
                return (
                    ExecutionStrategy.LIMIT
                    if signal.position_size <= 5000
                    else ExecutionStrategy.TWAP
                )
            elif score >= 0.6:
                if spr <= 0.005:
                    return ExecutionStrategy.MARKET
                return (
                    ExecutionStrategy.STOP_LIMIT
                    if vol >= 0.3
                    else ExecutionStrategy.LIMIT
                )
            elif score >= 0.4:
                return (
                    ExecutionStrategy.ICEBERG if liq <= 0.4 else ExecutionStrategy.VWAP
                )
            else:
                return ExecutionStrategy.MARKET

        except Exception as e:
            self.log.error(f"Strategy optimization failed: {e}")
            return ExecutionStrategy.MARKET


# ---------------------------------------------------------------------------
# Quantum timing enhancer with safe bounds
# ---------------------------------------------------------------------------
class QuantumExecutionEnhancer:
    def __init__(self):
        self.log = logging.getLogger(f"{__name__}.QuantumExecutionEnhancer")

    def optimize_execution_timing(
        self, order: ExecutionOrder, market: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            spr = float(market.get("spread", 0.01))
            vprof = float(market.get("volume_profile", 0.5))
            mom = float(market.get("momentum", 0.0))

            q_unc = random.uniform(0.85, 1.15)
            coherence = max(0.0, min(order.symbolic_coherence, 1.0))

            base_delay = {
                ExecutionStrategy.MARKET: 0.0,
                ExecutionStrategy.LIMIT: 60.0,
                ExecutionStrategy.STOP: 30.0,
                ExecutionStrategy.STOP_LIMIT: 45.0,
                ExecutionStrategy.TWAP: 300.0,
                ExecutionStrategy.VWAP: 180.0,
                ExecutionStrategy.ICEBERG: 120.0,
                ExecutionStrategy.SYMBOLIC_OPTIMAL: 30.0,
            }.get(order.strategy, 30.0)

            # Symbolic optimal gets finer control via spread & coherence
            if order.strategy == ExecutionStrategy.SYMBOLIC_OPTIMAL:
                delay = (
                    base_delay * (1 + min(spr * 100, 1.0)) * q_unc * max(0.5, coherence)
                )
            else:
                delay = base_delay * (1 + (1 - vprof) * 0.5) * max(0.5, coherence)

            delay = max(0.0, min(delay, 300.0))  # cap to 5 minutes

            # Priority tweak (±3)
            prio = order.execution_priority
            prio_adj = int(
                max(-3, min(3, abs(mom) * 2 + (q_unc - 1.0) * 3 + coherence * 2))
            )
            prio = max(1, min(10, prio + prio_adj))

            return {
                "optimal_delay_seconds": delay,
                "execution_priority": prio,
                "quantum_confidence": coherence,
                "timing_recommendation": (
                    "immediate"
                    if delay <= 5
                    else (
                        "short_delay"
                        if delay <= 30
                        else (
                            "medium_delay"
                            if delay <= 120
                            else "long_delay" if delay <= 300 else "extended_delay"
                        )
                    )
                ),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.log.error(f"Timing optimization failed: {e}")
            return {"optimal_delay_seconds": 0, "execution_priority": 5}


# ---------------------------------------------------------------------------
# Ethically-gated executor
# ---------------------------------------------------------------------------
class TradeExecutionEngine:
    def __init__(self, engine_directory: Optional[str] = None):
        self.log = logging.getLogger(f"{__name__}.TradeExecutionEngine")
        self.engine_directory = Path(engine_directory or "execution_engine_data")
        self.engine_directory.mkdir(exist_ok=True)

        self.symbolic_optimizer = SymbolicExecutionOptimizer()
        self.quantum_enhancer = QuantumExecutionEnhancer()

        self.active_orders: Dict[str, ExecutionOrder] = {}
        self.execution_history: Dict[str, ExecutionOrder] = {}
        self.metrics = ExecutionMetrics()

        # sensible ceilings for the first private phase
        self.max_orders_per_symbol = 10
        self.max_daily_orders = 200
        self.execution_timeout_s = 3600

        self.log.info("Trade Execution Engine v4.1+ initialized | SE41+Ethos+Quantum")

    # ---------------------------- public API ---------------------------------

    async def execute_trade_signal(
        self, signal: Any, market_conditions: Dict[str, Any]
    ) -> ExecutionOrder:
        """
        End-to-end: ethos-gate → strategy → timing → submit.
        """
        # 1) Ethos gate (at the very end of pipeline)
        if not self._ethos_allows(signal, market_conditions):
            oid = f"order_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            order = ExecutionOrder(
                order_id=oid,
                signal_id=signal.signal_id,
                symbol=signal.symbol,
                trade_type=signal.trade_type,
                quantity=signal.position_size,
                price=None,
                strategy=ExecutionStrategy.LIMIT,
                status=ExecutionStatus.REJECTED,
                symbolic_coherence=signal.symbolic_validation,
                quantum_probability=signal.quantum_probability,
            )
            self.log.info("Ethos denied/held: order rejected safely.")
            return order

        # 2) Strategy selection (SE41 numeric)
        strategy = self.symbolic_optimizer.optimize_execution_strategy(
            signal, market_conditions
        )

        # 3) Build order shell
        order = ExecutionOrder(
            order_id=f"order_{int(time.time())}_{uuid.uuid4().hex[:8]}",
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            trade_type=signal.trade_type,
            quantity=max(0.0, float(signal.position_size)),
            price=signal.entry_price if strategy != ExecutionStrategy.MARKET else None,
            strategy=strategy,
            symbolic_coherence=max(0.0, min(signal.symbolic_validation, 1.0)),
            quantum_probability=max(0.0, min(signal.quantum_probability, 1.0)),
            execution_priority=5,
        )

        # 4) Timing optimization
        timing = self.quantum_enhancer.optimize_execution_timing(
            order, market_conditions
        )
        order.execution_priority = timing.get("execution_priority", 5)

        # 5) Store and dispatch
        self.active_orders[order.order_id] = order
        await self._dispatch(order, timing)

        self.log.info(
            f"Execution initiated: {order.symbol} {order.trade_type.value} "
            f"strategy={order.strategy.value} prio={order.execution_priority}"
        )
        return order

    # --------------------------- internals -----------------------------------

    def _ethos_allows(self, signal: Any, market: Dict[str, Any]) -> bool:
        """
        Build an SE41 signals packet and query the ethos gate.
        """
        risk_hint = self._risk_hint_from_signal(signal)
        sig = se41_signals(
            {
                "coherence": max(0.0, min(signal.symbolic_validation, 1.0)),
                "risk": risk_hint,
                "impetus": max(
                    0.0, min(signal.confidence * market.get("liquidity", 0.7), 1.0)
                ),
                "ethos": {
                    "authenticity": 0.92,
                    "integrity": 0.90,
                    "responsibility": max(0.0, min(1.0 - risk_hint, 1.0)),
                    "enrichment": max(
                        0.0,
                        min(
                            market.get("breadth", 0.5) * market.get("liquidity", 0.7),
                            1.0,
                        ),
                    ),
                },
                "explain": "trade_execution.ethos_gate",
            }
        ) or {}
        decision = ethos_decision_envelope(
            sig
        )  # {'decision': 'allow'|'hold'|'deny', 'pillars': {...}, 'reason': ...}
        self._last_ethos = decision
        d = decision.get("decision", "hold")
        self.log.info(f"Ethos gate: {d} | reason={decision.get('reason','')}")
        return d == "allow"

    def _risk_hint_from_signal(self, signal: Any) -> float:
        level = str(getattr(signal, "risk_level", "medium")).lower()
        return {
            "minimal": 0.1,
            "low": 0.25,
            "medium": 0.5,
            "high": 0.75,
            "extreme": 0.9,
        }.get(level, 0.5)

    async def _dispatch(self, order: ExecutionOrder, timing: Dict[str, Any]) -> None:
        try:
            delay = float(timing.get("optimal_delay_seconds", 0.0))
            if delay > 0:
                await asyncio.sleep(min(delay, 300.0))  # hard cap

            # Pick the concrete path
            strat = order.strategy
            if strat == ExecutionStrategy.MARKET:
                await self._execute_market(order)
            elif strat == ExecutionStrategy.LIMIT:
                await self._execute_limit(order)
            elif strat == ExecutionStrategy.SYMBOLIC_OPTIMAL:
                await self._execute_symbolic_optimal(order)
            elif strat == ExecutionStrategy.TWAP:
                await self._execute_twap(order)
            elif strat == ExecutionStrategy.VWAP:
                await self._execute_vwap(order)
            elif strat in (
                ExecutionStrategy.STOP,
                ExecutionStrategy.STOP_LIMIT,
                ExecutionStrategy.ICEBERG,
            ):
                # For private alpha, route rare paths to limit for safety
                await self._execute_limit(order)
            else:
                await self._execute_market(order)

        except Exception as e:
            self.log.error(f"Dispatch failed: {e}")
            order.status = ExecutionStatus.REJECTED

    # ---- concrete paths (simulated for private phase) -----------------------

    async def _execute_market(self, order: ExecutionOrder) -> None:
        try:
            t0 = time.perf_counter()
            # simulate fill with small slippage
            slip = random.uniform(-0.002, 0.002)  # ±0.2%
            px = order.price if order.price is not None else 100.0
            fill_px = px * (1 + slip)
            fees = order.quantity * fill_px * 0.0005

            order.status = ExecutionStatus.FILLED
            order.filled_quantity = order.quantity
            order.average_price = fill_px
            order.fees = fees
            order.slippage = abs(slip)
            order.last_update = datetime.now()

            self._update_metrics(order, t0)
            self.log.info(
                f"Market filled: {order.symbol} @ {fill_px:.4f} | slip={order.slippage:.4%}"
            )

        except Exception as e:
            self.log.error(f"Market execution failed: {e}")
            order.status = ExecutionStatus.REJECTED

    async def _execute_limit(self, order: ExecutionOrder) -> None:
        try:
            t0 = time.perf_counter()
            base_px = order.price if order.price is not None else 100.0
            # Simulate partial improvement for coherent orders
            improve = order.symbolic_coherence * 0.0005  # up to 5 bps
            fill_px = base_px * (1 - improve)
            fees = order.quantity * fill_px * 0.0004

            order.status = ExecutionStatus.FILLED
            order.filled_quantity = order.quantity
            order.average_price = fill_px
            order.fees = fees
            order.slippage = max(0.0, 0.0002 - improve)  # modest slippage if any
            order.last_update = datetime.now()

            self._update_metrics(order, t0)
            self.log.info(
                f"Limit filled: {order.symbol} @ {fill_px:.4f} | improv={improve*10000:.2f}bps"
            )

        except Exception as e:
            self.log.error(f"Limit execution failed: {e}")
            order.status = ExecutionStatus.REJECTED

    async def _execute_symbolic_optimal(self, order: ExecutionOrder) -> None:
        try:
            t0 = time.perf_counter()
            base_px = order.price if order.price is not None else 100.0
            # Symbolic + quantum improvement
            imp = order.symbolic_coherence * 0.001  # up to 10 bps
            q_adj = (order.quantum_probability - 0.5) * 0.0005  # ±5 bps
            fill_px = base_px * (1 - imp + q_adj)
            fees = order.quantity * fill_px * 0.0003

            success = random.random() < (
                order.symbolic_coherence * max(0.4, order.quantum_probability)
            )
            if success:
                order.status = ExecutionStatus.FILLED
                order.filled_quantity = order.quantity
                order.average_price = fill_px
                order.fees = fees
                order.slippage = max(0.0, 0.00015 - imp)
                order.last_update = datetime.now()
                self._update_metrics(order, t0)
                self.log.info(
                    f"Symbolic-optimal filled: {order.symbol} @ {fill_px:.4f} | "
                    f"imp={imp*10000:.2f}bps q={q_adj*10000:.2f}bps"
                )
            else:
                # fallback to limit
                await self._execute_limit(order)

        except Exception as e:
            self.log.error(f"Symbolic-optimal failed: {e}")
            await self._execute_market(order)

    async def _execute_twap(self, order: ExecutionOrder) -> None:
        # Private alpha: simulate consolidated fill
        await self._execute_limit(order)

    async def _execute_vwap(self, order: ExecutionOrder) -> None:
        # Private alpha: simulate consolidated fill
        await self._execute_limit(order)

    # ---------------------------- telemetry ----------------------------------

    def _update_metrics(self, order: ExecutionOrder, t0: float) -> None:
        try:
            self.metrics.total_orders += 1
            if order.status == ExecutionStatus.FILLED:
                self.metrics.filled_orders += 1
                # fill time
                dt_ms = (time.perf_counter() - t0) * 1000.0
                n = self.metrics.filled_orders
                self.metrics.average_fill_time_ms = (
                    self.metrics.average_fill_time_ms * (n - 1) + dt_ms
                ) / n
                # average slippage
                self.metrics.average_slippage = (
                    self.metrics.average_slippage * (n - 1) + order.slippage
                ) / n
                # fees & symbolic alignment
                self.metrics.total_fees += order.fees
                self.metrics.symbolic_alignment_score = (
                    self.metrics.symbolic_alignment_score * (n - 1)
                    + order.symbolic_coherence
                ) / n

            elif order.status == ExecutionStatus.CANCELLED:
                self.metrics.cancelled_orders += 1

            # execution quality (0..1)
            fill_rate = self.metrics.filled_orders / max(self.metrics.total_orders, 1)
            slip_quality = max(
                0.0, 1.0 - self.metrics.average_slippage * 1000.0
            )  # lower slippage → higher score
            sym_quality = self.metrics.symbolic_alignment_score
            self.metrics.execution_quality_score = round(
                fill_rate * 0.4 + slip_quality * 0.3 + sym_quality * 0.3, 4
            )
        except Exception as e:
            self.log.error(f"Metrics update failed: {e}")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_trade_execution_engine(**kwargs) -> TradeExecutionEngine:
    return TradeExecutionEngine(**kwargs)


# ---------------------------------------------------------------------------
# Smoke (local)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    eng = create_trade_execution_engine()

    # Minimal signal+market for smoke
    if TRADE_EXECUTOR_AVAILABLE:
        from trading_engine.ai_trade_executor import MarketType, RiskLevel

        sig = TradingSignal(
            signal_id=f"sig_{uuid.uuid4().hex[:6]}",
            symbol="AAPL",
            market_type=MarketType.STOCKS,
            trade_type=TradeType.BUY,
            confidence=0.72,
            risk_level=RiskLevel.MODERATE,
            entry_price=195.25,
            target_price=205.0,
            stop_loss=182.0,
            position_size=100.0,
            reasoning="smoke-test",
            symbolic_validation=0.78,
            quantum_probability=0.62,
        )
    else:
        SignalCtor = cast(Any, TradingSignal)
        sig = SignalCtor(
            signal_id=f"sig_{uuid.uuid4().hex[:6]}",
            symbol="AAPL",
            market_type="stocks",
            trade_type=TradeType.BUY,
            position_size=100.0,
            entry_price=195.25,
            confidence=0.72,
            risk_level="medium",
            target_price=205.0,
            stop_loss=182.0,
            reasoning="smoke-test",
            symbolic_validation=0.78,
            quantum_probability=0.62,
        )
    mkt = {
        "volatility": 0.22,
        "liquidity": 0.78,
        "spread": 0.004,
        "volume": 4_500_000,
        "breadth": 0.61,
        "volume_profile": 0.55,
        "momentum": 0.18,
    }

    async def main():
        order = await eng.execute_trade_signal(sig, mkt)
        print("ORDER:", order)
        print("METRICS:", eng.metrics)

    asyncio.run(main())

# Why this matters
# Execution is the riskiest hop. Now, every order must pass SE41 and an Ethos gate right before it hits the pipe.
# Private alpha safe by default. Even “symbolic optimal” has hardened fallbacks and bounded timing.
# Observability built-in. Execution quality distills what matters: fill rate, slippage quality, symbolic alignment.
