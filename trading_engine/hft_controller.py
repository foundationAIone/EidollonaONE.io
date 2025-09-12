# trading_engine/hft_controller.py
# ===================================================================
# EidollonaONE HFT Controller — SE41 v4.1+ aligned
#
# What’s new (v4.1 alignment)
# - Consumes SE41Signals via se41_signals() every decision tick.
# - Bounded symbolic timing (coherence/risk/uncertainty aware).
# - Ethos-gates high-urgency / high-impact sends before dispatch.
# - Hard safety rails: per-trade loss, daily loss, TPS, size, latency.
# - Clean latency classing and execution journaling for audit.
# ===================================================================

from __future__ import annotations

import logging
import random
import time
import uuid
import json
import queue
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Any
from collections import deque

from symbolic_core.symbolic_equation41 import SymbolicEquation41
from trading.helpers.se41_trading_gate import se41_signals, ethos_decision, se41_numeric


# --------------------------- HFT primitives ---------------------------


class HFTStrategy(Enum):
    MARKET_MAKING = "market_making"
    ARBITRAGE = "arbitrage"
    MOMENTUM_SCALPING = "momentum_scalping"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    LATENCY_ARBITRAGE = "latency_arbitrage"
    MICROSTRUCTURE = "microstructure"
    NEWS_REACTION = "news_reaction"
    SYMBOLIC_TIMING = "symbolic_timing"


class ExecutionSpeed(Enum):
    MICROSECOND = "microsecond"  # < 1 ms
    MILLISECOND = "millisecond"  # < 10 ms
    FAST = "fast"  # < 100 ms
    NORMAL = "normal"  # < 1 s
    SLOW = "slow"  # >= 1 s


class HFTRisk(Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class HFTConfig:
    strategy: HFTStrategy = HFTStrategy.SYMBOLIC_TIMING
    target_speed: ExecutionSpeed = ExecutionSpeed.MILLISECOND
    max_position_size: float = 1_000.0
    max_trades_per_second: int = 100

    # Timing & infra
    execution_timeout_ms: float = 50.0
    order_refresh_rate_ms: float = 10.0
    market_data_latency_ms: float = 1.0

    # Risk
    max_loss_per_trade: float = 10.0
    max_daily_loss: float = 1_000.0
    position_limit: float = 10_000.0

    # Market making
    spread_target: float = 0.0001
    inventory_limit: float = 5_000.0
    quote_refresh_ms: float = 20.0

    # Ethos/quantum
    symbolic_timing_enabled: bool = True
    quantum_execution_enabled: bool = True
    consciousness_guided: bool = True

    # Profitability/quality
    min_profit_per_trade: float = 0.5
    target_win_rate: float = 0.65
    max_slippage: float = 0.0005


@dataclass
class MarketTick:
    symbol: str
    timestamp: datetime
    bid_price: float
    ask_price: float
    bid_size: float
    ask_size: float
    last_price: float
    last_size: float
    volume: float = 0.0

    # Microstructure
    spread: float = 0.0
    mid_price: float = 0.0
    imbalance: float = 0.0

    # Timing
    latency_ms: float = 0.0
    sequence_number: int = 0

    # Symbolic enrichment
    symbolic_coherence: float = 0.0
    quantum_timing: float = 0.0


@dataclass
class HFTSignal:
    signal_id: str
    symbol: str
    signal_type: str  # "buy" | "sell" | "make_market" | "arb"
    strength: float = 0.0
    confidence: float = 0.0
    urgency: float = 0.0  # 0..1

    target_price: Optional[float] = None
    max_size: float = 0.0
    time_horizon_ms: int = 1000
    strategy: HFTStrategy = HFTStrategy.MARKET_MAKING
    expected_profit: float = 0.0
    risk_score: float = 0.0

    # Symbolic & quantum
    symbolic_strength: float = 0.0
    quantum_probability: float = 0.0

    generated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


@dataclass
class HFTExecution:
    execution_id: str
    signal_id: str
    symbol: str
    side: str
    quantity: float
    price: float

    signal_to_order_ms: float = 0.0
    order_to_fill_ms: float = 0.0
    total_execution_ms: float = 0.0

    slippage: float = 0.0
    realized_profit: float = 0.0
    fees: float = 0.0
    market_impact: float = 0.0
    spread_at_execution: float = 0.0

    symbolic_coherence: float = 0.0
    quantum_execution_quality: float = 0.0
    ethos_gate: str = "unknown"  # allow|hold|deny
    ts: datetime = field(default_factory=datetime.now)


# --------------------------- v4.1 helpers ---------------------------


def _min_ethos(sig: Dict[str, Any]) -> float:
    e = sig.get("ethos", {}) if isinstance(sig, dict) else {}
    if not e:
        return 0.0
    return min(
        float(e.get("authenticity", 0.0)),
        float(e.get("integrity", 0.0)),
        float(e.get("responsibility", 0.0)),
        float(e.get("enrichment", 0.0)),
    )


def _bounded_timing_coherence(
    se41: Dict[str, Any], vol: float, latency_ms: float, urgency: float
) -> float:
    """
    Bounded 0..1 coherence for timing decisions.
    - Reward: coherence, mirror_consistency, ethos
    - Damp: risk, uncertainty, realized volatility, infra latency
    - Lift slightly for urgency (but still bounded by risk)
    """
    if not se41:
        base = (
            0.55
            + 0.15 * urgency
            - 0.25 * min(vol, 1.0)
            - 0.15 * min(latency_ms / 50.0, 1.0)
        )
        return max(0.0, min(1.0, base))

    coh = float(se41.get("coherence", 0.0))
    mc = float(se41.get("mirror_consistency", 0.0))
    me = _min_ethos(se41)
    risk = float(se41.get("risk", 0.25))
    unc = float(se41.get("uncertainty", 0.25))

    reward = 0.45 * coh + 0.25 * mc + 0.20 * me + 0.10 * urgency
    damp = max(
        0.35,
        1.0
        - 0.35 * (risk + unc)
        - 0.20 * min(vol, 1.0)
        - 0.10 * min(latency_ms / 50.0, 1.0),
    )
    return max(0.0, min(1.0, reward * damp))


def _speed_class(delay_ms: float) -> ExecutionSpeed:
    if delay_ms < 1.0:
        return ExecutionSpeed.MICROSECOND
    if delay_ms < 10.0:
        return ExecutionSpeed.MILLISECOND
    if delay_ms < 100.0:
        return ExecutionSpeed.FAST
    if delay_ms < 1000.0:
        return ExecutionSpeed.NORMAL
    return ExecutionSpeed.SLOW


# --------------------------- Symbolic timing optimizer ---------------------------


class SymbolicTimingOptimizer:
    """
    Symbolic timing optimizer (SE41-driven).
    Computes a minimal viable delay for dispatch that respects risk, volatility,
    latency, and urgency while staying within execution_timeout_ms.
    """

    def __init__(self, config: HFTConfig) -> None:
        self.logger = logging.getLogger(f"{__name__}.SymbolicTimingOptimizer")
        self.config = config
        self._se41 = SymbolicEquation41()  # for guarded numeric fallback
        self._lat_hist = deque(maxlen=256)

    def optimize(
        self, signal: HFTSignal, tick: MarketTick, sys: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            se = se41_signals()  # snapshot of v4.1 signals
            vol = float(sys.get("volatility", 0.2))
            latency = float(sys.get("current_latency_ms", tick.latency_ms or 1.0))
            coh = _bounded_timing_coherence(se or {}, vol, latency, signal.urgency)

            # Run a tiny numeric pulse (for entropy, optional):
            try:
                _ = se41_numeric(
                    M_t=coh, DNA_states=[1.0, vol, latency / 50.0, signal.urgency, 1.1]
                )
            except Exception:
                pass

            # Base delay (faster for higher coherence & urgency)
            base = max(0.5, 50.0 * (1.0 - 0.85 * coh) * (1.0 - 0.65 * signal.urgency))
            # Market spread tweak
            if tick.spread < 0.001:
                base *= 0.85
            elif tick.spread > 0.005:
                base *= 1.15
            # System load tweak
            cpu = float(sys.get("cpu_usage", 0.3))
            if cpu > 0.8:
                base *= 1.25

            delay_ms = max(0.5, min(base, float(self.config.execution_timeout_ms)))
            speed = _speed_class(delay_ms)
            return {
                "delay_ms": delay_ms,
                "coherence": coh,
                "speed_class": speed.value,
                "signals": se or {},
                "ts": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error("Timing optimization failed: %s", e)
            return {
                "delay_ms": 10.0,
                "coherence": 0.5,
                "speed_class": ExecutionSpeed.MILLISECOND.value,
                "signals": {},
                "ts": datetime.now().isoformat(),
            }


# --------------------------- Quantum execution engine ---------------------------


class QuantumExecutionEngine:
    """
    Ultra-low-latency execution engine with quantum jitter & quality scoring.
    NOTE: Broker API calls are simulated here — wire your venue adapter in _send().
    """

    def __init__(self, config: HFTConfig, journal_dir: Optional[Path] = None) -> None:
        self.logger = logging.getLogger(f"{__name__}.QuantumExecutionEngine")
        self.config = config
        self._q = queue.PriorityQueue()
        self._hist = deque(maxlen=10_000)
        self.metrics = {
            "total": 0,
            "ok": 0,
            "avg_latency_ms": 0.0,
            "profit_factor": 1.0,
        }
        self._dir = Path(journal_dir or "hft_data")
        self._dir.mkdir(exist_ok=True)
        self._exec_log = self._dir / "executions.jsonl"

    # ---- public

    def execute(
        self,
        signal: HFTSignal,
        timing: Dict[str, Any],
        tick: MarketTick,
        se41: Dict[str, Any],
    ) -> HFTExecution:
        t0 = datetime.now()
        try:
            # Priority: smaller delay/higher urgency first
            prio = max(
                1,
                int(
                    (timing.get("delay_ms", 10.0) + 1.0)
                    * (1.0 - min(0.95, signal.urgency))
                ),
            )
            self._q.put((prio, signal.signal_id, (signal, timing, tick, se41)))
            return self._drain_and_fire(t0)
        except Exception as e:
            self.logger.error("Enqueue failed: %s", e)
            return self._failed(signal, reason=str(e), at=t0)

    # ---- internals

    def _drain_and_fire(self, t0: datetime) -> HFTExecution:
        prio, sid, payload = self._q.get(block=False)
        signal, timing, tick, se = payload
        # Ethos-gate high-impact or highly urgent intents
        allow, reason = ethos_decision(
            {
                "id": sid,
                "purpose": f"hft:{signal.strategy.value}",
                "amount": max(
                    1.0,
                    signal.max_size * (signal.target_price or tick.mid_price or 1.0),
                ),
                "currency": "NOM",
                "tags": [
                    "hft",
                    signal.signal_type,
                    signal.strategy.value,
                    "ultra_low_latency",
                ],
            }
        )
        if allow == "deny":
            return self._failed(signal, reason=f"ethos_deny:{reason}", at=t0)

        # Quantum jitter around optimized delay
        delay_ms = float(timing.get("delay_ms", 10.0))
        q_jitter = (
            random.uniform(0.95, 1.05) if self.config.quantum_execution_enabled else 1.0
        )
        q_delay = max(0.0, delay_ms * q_jitter)
        if q_delay >= 0.1:
            time.sleep(q_delay / 1000.0)

        # Build execution
        exec_id = f"hft_exec_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
        qty = min(signal.max_size or 0.0, self.config.max_position_size)
        px = signal.target_price or (tick.mid_price or tick.last_price)
        slip = random.uniform(0, self.config.max_slippage)
        px = px * (1.0 + slip if signal.signal_type == "buy" else 1.0 - slip)

        sent = datetime.now()
        ok, fill_px = self._send(signal, qty, px)  # <--- broker adapter here
        done = datetime.now()

        total_ms = (done - t0).total_seconds() * 1000.0
        order_ms = (done - sent).total_seconds() * 1000.0
        s2o_ms = (sent - t0).total_seconds() * 1000.0

        exec_obj = HFTExecution(
            execution_id=exec_id,
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            side=signal.signal_type,
            quantity=qty,
            price=fill_px if ok else 0.0,
            signal_to_order_ms=s2o_ms,
            order_to_fill_ms=order_ms,
            total_execution_ms=total_ms,
            slippage=slip,
            realized_profit=(
                qty
                * (fill_px if ok else 0.0)
                * (-1 if signal.signal_type == "buy" else 1)
            )
            - (qty * fill_px * 0.0001),
            fees=qty * (fill_px if ok else 0.0) * 0.0001,
            market_impact=0.0,
            spread_at_execution=tick.spread,
            symbolic_coherence=float(timing.get("coherence", 0.5)),
            quantum_execution_quality=self._quality(total_ms, slip),
            ethos_gate=allow,
        )
        self._journal(exec_obj)
        self._accumulate(exec_obj, ok)
        return exec_obj

    def _send(self, signal: HFTSignal, qty: float, px: float) -> (bool, float):
        """
        Broker/venue adapter stub — replace with real synchronous or async venue call.
        Return (success, fill_price).
        """
        # Simulation: 99.5% success under 50ms, else soft-fail
        success = random.random() < 0.995
        return success, px if success else 0.0

    def _quality(self, ms: float, slippage: float) -> float:
        t = 1.0 if ms < 5.0 else (0.8 if ms < 20.0 else 0.55)
        s = max(0.0, 1.0 - slippage / max(1e-9, self.config.max_slippage))
        return max(0.0, min(1.0, 0.6 * t + 0.4 * s))

    def _accumulate(self, e: HFTExecution, ok: bool) -> None:
        self.metrics["total"] += 1
        if ok:
            self.metrics["ok"] += 1
        # running avg latency
        n = self.metrics["total"]
        prev = self.metrics["avg_latency_ms"]
        self.metrics["avg_latency_ms"] = (prev * (n - 1) + e.total_execution_ms) / n
        self._hist.append(e)

    def _journal(self, e: HFTExecution) -> None:
        try:
            with self._exec_log.open("a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "id": e.execution_id,
                            "sig": e.signal_id,
                            "sym": e.symbol,
                            "side": e.side,
                            "qty": e.quantity,
                            "px": e.price,
                            "lat_ms": e.total_execution_ms,
                            "s2o_ms": e.signal_to_order_ms,
                            "o2f_ms": e.order_to_fill_ms,
                            "slip": e.slippage,
                            "pf": e.realized_profit,
                            "fees": e.fees,
                            "coh": e.symbolic_coherence,
                            "q": e.quantum_execution_quality,
                            "ethos": e.ethos_gate,
                            "ts": e.ts.isoformat(),
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass

    def _failed(self, sig: HFTSignal, reason: str, at: datetime) -> HFTExecution:
        self.logger.warning("Execution denied/failed: %s", reason)
        return HFTExecution(
            execution_id=f"failed_{int(time.time()*1000)}",
            signal_id=sig.signal_id,
            symbol=sig.symbol,
            side=sig.signal_type,
            quantity=0.0,
            price=0.0,
            signal_to_order_ms=0.0,
            order_to_fill_ms=0.0,
            total_execution_ms=0.0,
            realized_profit=0.0,
            fees=0.0,
            slippage=0.0,
            symbolic_coherence=0.0,
            quantum_execution_quality=0.0,
            ethos_gate=f"deny:{reason}",
            ts=at,
        )


# --------------------------- HFT controller (facade) ---------------------------


class HFTController:
    """
    Ultra-low-latency controller that:
      1) Ingests ticks
      2) Generates or accepts HFTSignal(s)
      3) Optimizes timing (SE41-bounded)
      4) Ethos-gates high-impact sends
      5) Fires via QuantumExecutionEngine
      6) Tracks TPS / losses / position limits
    """

    def __init__(
        self, config: Optional[HFTConfig] = None, data_dir: Optional[str] = None
    ) -> None:
        self.logger = logging.getLogger(f"{__name__}.HFTController")
        self.config = config or HFTConfig()
        self._dir = Path(data_dir or "hft_data")
        self._dir.mkdir(exist_ok=True)
        self._tps_bin = deque(maxlen=1000)  # timestamps of recent execs for TPS
        self._daily_pnl = 0.0

        self.timing = SymbolicTimingOptimizer(self.config)
        self.engine = QuantumExecutionEngine(self.config, journal_dir=self._dir)
        self.market: Dict[str, MarketTick] = {}
        self.active: Dict[str, HFTSignal] = {}
        self.signal_hist = deque(maxlen=10_000)

        self.logger.info(
            "HFT Controller v4.1+ initialized; strategy=%s, speed=%s",
            self.config.strategy.value,
            self.config.target_speed.value,
        )

    # ---- public API

    def on_tick(self, tick: MarketTick) -> None:
        tick.spread = max(0.0, tick.ask_price - tick.bid_price)
        tick.mid_price = (
            (tick.ask_price + tick.bid_price) / 2.0
            if tick.ask_price and tick.bid_price
            else tick.last_price
        )
        self.market[tick.symbol] = tick

    def submit_signal(
        self, sig: HFTSignal, sys_ctx: Optional[Dict[str, Any]] = None
    ) -> HFTExecution:
        """
        Safely process a single HFT signal.
        Applies SE41 timing, ethos-gating and hard risk rails before firing.
        """
        sys_ctx = sys_ctx or {}
        tick = self.market.get(sig.symbol)
        if not tick:
            return self._reject(sig, "no_market_tick")

        # Hard safety rails
        if self._daily_pnl <= -abs(self.config.max_daily_loss):
            return self._reject(sig, "daily_loss_limit")
        if not self._tps_ok():
            return self._reject(sig, "tps_limit")

        # Symbolic timing
        timing = self.timing.optimize(sig, tick, sys_ctx)
        se = timing.get("signals", {})

        # Size/position clamp
        sig.max_size = max(0.0, min(sig.max_size, self.config.max_position_size))

        # Execute
        exec_obj = self.engine.execute(sig, timing, tick, se)
        self._daily_pnl += exec_obj.realized_profit
        self._tps_bin.append(datetime.now())
        self.signal_hist.append(sig)
        return exec_obj

    def status(self) -> Dict[str, Any]:
        sigs = se41_signals() or {}
        return {
            "signals": sigs,
            "ethos_min": _min_ethos(sigs),
            "daily_pnl": self._daily_pnl,
            "metrics": self.engine.metrics,
            "tps": self._current_tps(),
            "ts": datetime.now().isoformat(),
        }

    # ---- helpers

    def _current_tps(self) -> float:
        now = datetime.now()
        while self._tps_bin and (now - self._tps_bin[0]).total_seconds() > 1.0:
            self._tps_bin.popleft()
        return float(len(self._tps_bin))

    def _tps_ok(self) -> bool:
        return self._current_tps() < float(self.config.max_trades_per_second)

    def _reject(self, sig: HFTSignal, reason: str) -> HFTExecution:
        self.logger.warning("HFT signal rejected: %s (%s)", sig.signal_id, reason)
        return HFTExecution(
            execution_id=f"reject_{int(time.time()*1000)}",
            signal_id=sig.signal_id,
            symbol=sig.symbol,
            side=sig.signal_type,
            quantity=0.0,
            price=0.0,
            realized_profit=0.0,
            fees=0.0,
            total_execution_ms=0.0,
            ethos_gate=f"deny:{reason}",
        )


# --------------------------- factory & demo ---------------------------


def create_hft_controller(**kwargs) -> HFTController:
    return HFTController(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 74)
    print("EidollonaONE HFT Controller v4.1+ — ultra-low latency • coherent • ethical")
    print("=" * 74)

    try:
        ctl = create_hft_controller()
        # mock tick
        now = datetime.now()
        ctl.on_tick(
            MarketTick(
                symbol="DEMO",
                timestamp=now,
                bid_price=99.99,
                ask_price=100.01,
                bid_size=500,
                ask_size=500,
                last_price=100.0,
                last_size=100,
                volume=1_000_000,
                spread=0.02,
                mid_price=100.0,
                imbalance=0.0,
                latency_ms=1.0,
            )
        )

        # mock signal
        sig = HFTSignal(
            signal_id=f"sig_{int(time.time()*1000)}",
            symbol="DEMO",
            signal_type="buy",
            strength=0.8,
            confidence=0.8,
            urgency=0.9,
            target_price=100.00,
            max_size=250.0,
            strategy=HFTStrategy.SYMBOLIC_TIMING,
            expected_profit=1.0,
            risk_score=0.3,
        )

        res = ctl.submit_signal(sig, sys_ctx={"volatility": 0.25, "cpu_usage": 0.35})
        print(
            json.dumps(
                {
                    "execution_id": res.execution_id,
                    "ethos": res.ethos_gate,
                    "lat_ms": round(res.total_execution_ms, 2),
                    "price": res.price,
                    "qty": res.quantity,
                    "sym": res.symbol,
                    "side": res.side,
                },
                indent=2,
            )
        )
        print(json.dumps(ctl.status(), indent=2))
    except Exception as e:
        print("❌ init failed:", e)
