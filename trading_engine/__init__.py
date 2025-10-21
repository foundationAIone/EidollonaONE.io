"""trading_engine (SE41 v4.1+ Facade)

Production-aligned consolidated trading engine facade. Provides a single,
symbolic-first entrypoint coordinating:
  * Signal generation (if AI module present)
  * SE41 evaluation (coherence, risk, impetus, ethos pillars)
  * Ethos gating (allow/hold/deny) and bounded proceed rules
  * Execution dispatch (paper by default; optional execution engine)
  * Portfolio & risk telemetry

Design Goals:
  - Graceful degradation: Missing optional subsystems never break imports
  - Bounded semantics: All scoring passes through SE41 bounded numeric logic
  - Explicit proceed gating: coherence & risk thresholds + ethos decision
  - Auditable simplicity: Single import path / minimal surface area
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

# --- SE41 core --------------------------------------------------------------
from symbolic_core.symbolic_equation41 import SymbolicEquation41, SE41Signals  # type: ignore
from symbolic_core.context_builder import assemble_se41_context  # type: ignore
from trading.helpers.se41_trading_gate import (
    se41_signals,  # -> SE41Signals payload builder
    ethos_decision,  # -> {decision: allow/hold/deny, pillars...}
)

# --- Optional subsystems (soft deps; facade will degrade gracefully) --------
try:  # Execution AI (signal discovery)
    from trading_engine.ai_trade_executor import AITradeExecutor, TradingSignal  # type: ignore

    _EXECUTOR_AVAILABLE = True
except Exception:  # pragma: no cover - optional
    _EXECUTOR_AVAILABLE = False
    AITradeExecutor = None  # type: ignore
    TradingSignal = None  # type: ignore

try:  # Concrete execution engine
    from trading_engine.trade_execution import TradeExecutionEngine  # type: ignore

    _EXEC_ENGINE_AVAILABLE = True
except Exception:  # pragma: no cover
    _EXEC_ENGINE_AVAILABLE = False
    TradeExecutionEngine = None  # type: ignore

try:  # Position manager
    from trading_engine.position_manager import PositionManager  # type: ignore

    _POS_MANAGER_AVAILABLE = True
except Exception:  # pragma: no cover
    _POS_MANAGER_AVAILABLE = False
    PositionManager = None  # type: ignore

try:  # PnL calculator
    from trading_engine.pnl_calculator import PnLCalculator, PnLPeriod  # type: ignore

    _PNL_AVAILABLE = True
except Exception:  # pragma: no cover
    _PNL_AVAILABLE = False
    PnLCalculator = None  # type: ignore
    PnLPeriod = None  # type: ignore


# ---------------------------------------------------------------------------
# Public facade types
# ---------------------------------------------------------------------------
@dataclass
class EngineConfig:
    enable_ethos_gate: bool = True
    min_coherence_allow: float = 0.65
    risk_hold_threshold: float = 0.6
    risk_deny_threshold: float = 0.85
    paper_trading: bool = True  # default to paper until explicitly armed
    max_daily_risk: float = 0.05  # 5% of portfolio
    max_position: float = 10_000.0


@dataclass
class ScoredSignal:
    """Unified scored signal representation used by the facade."""

    signal_id: str
    symbol: str
    trade_type: str
    entry_price: float
    position_size: float
    coherence: float
    risk: float
    impetus: float
    ethos: Dict[str, float]
    recommend: str
    proceed: bool
    explain: str = "ok"


class TradingEngine:
    """Symbolic-first consolidated trading engine (SE41 v4.1+)."""

    def __init__(self, config: Optional[EngineConfig] = None):
        self.log = logging.getLogger(f"{__name__}.TradingEngine")
        self.cfg = config or EngineConfig()
        self._se41 = SymbolicEquation41()
        # Optional subsystems (soft dependencies)
        # These soft deps may be None; ignore type checkers for callable usage
        self._ai = AITradeExecutor() if _EXECUTOR_AVAILABLE else None  # type: ignore[operator]
        self._exec = TradeExecutionEngine() if _EXEC_ENGINE_AVAILABLE else None  # type: ignore[operator]
        self._pos = PositionManager() if _POS_MANAGER_AVAILABLE else None  # type: ignore[operator]
        self._pnl = PnLCalculator() if _PNL_AVAILABLE else None  # type: ignore[operator]
        self._armed_live = not self.cfg.paper_trading
        self._last_status: Dict[str, Any] = {}
        self.log.info(
            "TradingEngine v4.1+ initialized "
            f"(ai={bool(self._ai)} exec={bool(self._exec)} pos={bool(self._pos)} pnl={bool(self._pnl)})"
        )

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------
    def generate_signals(
        self, watchlist: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        if not self._ai:
            self.log.warning(
                "generate_signals: AITradeExecutor not available; returning empty list."
            )
            return []
        out: List[Dict[str, Any]] = []
        symbols = watchlist or [
            "AAPL",
            "MSFT",
            "GOOGL",
            "TSLA",
            "BTC/USD",
            "ETH/USD",
            "EUR/USD",
        ]
        for s in symbols:
            try:
                result = self._ai.ai_intelligence.generate_trading_signal(  # type: ignore[union-attr]
                    symbol=s,
                    market_type=cast(Any, getattr(self._ai, "MarketType", None) or "stocks"),
                    market_data={"current_price": 100.0},
                )
            except Exception:
                result = None
            if result:
                out.append(self._to_dict_signal(result))
        return out

    def validate_and_score(self, raw_signal: Dict[str, Any]) -> ScoredSignal:
        symbol = raw_signal.get("symbol", "UNKNOWN")
        trade_type = str(raw_signal.get("trade_type", "buy"))
        entry = float(raw_signal.get("entry_price", raw_signal.get("price", 100.0)))
        size = float(raw_signal.get("position_size", 1000.0))
        ctx = assemble_se41_context(
            coherence_hint=float(raw_signal.get("symbolic_validation", 0.7)),
            risk_hint=0.2,
            uncertainty_hint=0.2,
            mirror_consistency=float(raw_signal.get("symbolic_validation", 0.7)),
            s_em=0.83,
        )
        s: SE41Signals = self._se41.evaluate(ctx)  # type: ignore
        sig_input: Dict[str, Any] = {
            "coherence": s.coherence,
            "risk": max(0.0, min(s.risk, 1.0)),
            "impetus": max(0.0, min(s.impetus, 1.0)),
            "ethos": s.ethos,
            "explain": f"symbol={symbol} trade={trade_type}",
        }
        sig = se41_signals(sig_input) or sig_input
        gate_raw = (
            ethos_decision(sig) if self.cfg.enable_ethos_gate else {"decision": "allow"}
        )
        # Normalize ethos_decision which may return tuple(decision, reason)
        if isinstance(gate_raw, tuple):
            decision, reason = gate_raw
            gate: Dict[str, Any] = {"decision": decision, "reason": reason}
        else:
            gate = cast(Dict[str, Any], gate_raw)
        decision = gate.get("decision", "hold")
        proceed = (
            decision in ("allow", "approve", "permit")
            and s.coherence >= self.cfg.min_coherence_allow
            and s.risk < self.cfg.risk_hold_threshold
        )
        return ScoredSignal(
            signal_id=raw_signal.get(
                "signal_id", f"sig_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            ),
            symbol=symbol,
            trade_type=trade_type,
            entry_price=entry,
            position_size=size,
            coherence=s.coherence,
            risk=s.risk,
            impetus=s.impetus,
            ethos=s.ethos,
            recommend="buy" if trade_type.lower().startswith("buy") else "sell",
            proceed=proceed,
            explain=s.explain or "ok",
        )

    async def execute(self, scored: ScoredSignal) -> Dict[str, Any]:
        if not scored.proceed:
            self.log.info(f"execute: proceed=False for {scored.symbol}; skipping")
            return {"ok": False, "reason": "not_proceed"}
        if not self._exec:
            self.log.warning("execute: TradeExecutionEngine not available")
            return {"ok": False, "reason": "exec_unavailable"}
        market = {
            "volatility": 0.2,
            "liquidity": 0.75,
            "spread": 0.005,
            "momentum": 0.1,
            "volume": 1_000_000,
        }
        if _EXECUTOR_AVAILABLE and hasattr(self._ai, "ai_intelligence"):
            ts = self._to_ai_signal(scored)
        else:
            ts = self._fabricate_exec_signal(scored)
        try:
            order = await self._exec.execute_trade_signal(ts, market)  # type: ignore
            return {
                "ok": True,
                "order_id": getattr(order, "order_id", None),
                "status": getattr(getattr(order, "status", None), "value", None),
                "avg_price": getattr(order, "average_price", None),
                "fees": getattr(order, "fees", None),
                "slippage": getattr(order, "slippage", None),
            }
        except Exception as e:  # pragma: no cover - defensive
            self.log.error(f"execute failed: {e}")
            return {"ok": False, "reason": str(e)}

    def portfolio_status(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"timestamp": datetime.now().isoformat()}
        try:
            if self._ai:
                out["executor"] = self._ai.get_portfolio_status()
                out["performance"] = self._ai.get_trading_performance()
        except Exception:
            out["executor"] = {}
        try:
            if self._pnl:
                out["pnl_hint"] = {"available": True}
            else:
                out["pnl_hint"] = {"available": False}
        except Exception:
            out["pnl_hint"] = {"available": False}
        self._last_status = out
        return out

    def risk_snapshot(self) -> Dict[str, Any]:
        last = self._last_status or {}
        win_rate = (last.get("performance") or {}).get("win_rate") or 0.0
        return {
            "ts": datetime.now().isoformat(),
            "paper": self.cfg.paper_trading and not self._armed_live,
            "max_daily_risk": self.cfg.max_daily_risk,
            "win_rate": win_rate,
            "coherence_hint": 0.8,
        }

    # -------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------
    def arm_live(self) -> None:
        self._armed_live = True
        self.cfg.paper_trading = False
        self.log.warning("TradingEngine armed for LIVE (ethos gate still active)")

    @staticmethod
    def _to_dict_signal(sig_obj: Any) -> Dict[str, Any]:
        try:
            return {
                "signal_id": getattr(
                    sig_obj, "signal_id", f"sig_{uuid.uuid4().hex[:8]}"
                ),
                "symbol": getattr(sig_obj, "symbol", "UNKNOWN"),
                "trade_type": getattr(sig_obj, "trade_type", "buy"),
                "entry_price": getattr(
                    sig_obj, "entry_price", getattr(sig_obj, "target_price", 100.0)
                ),
                "position_size": getattr(sig_obj, "position_size", 1000.0),
                "symbolic_validation": getattr(sig_obj, "symbolic_validation", 0.7),
                "win_rate": getattr(sig_obj, "win_rate", 0.5),
                "volatility": 0.2,
            }
        except Exception:
            return {
                "signal_id": f"sig_{uuid.uuid4().hex[:8]}",
                "symbol": "UNKNOWN",
                "trade_type": "buy",
                "entry_price": 100.0,
                "position_size": 1000.0,
                "symbolic_validation": 0.7,
            }

    @staticmethod
    def _fabricate_exec_signal(scored: ScoredSignal) -> Dict[str, Any]:
        return {
            "signal_id": scored.signal_id,
            "symbol": scored.symbol,
            "trade_type": scored.trade_type,
            "position_size": scored.position_size,
            "entry_price": scored.entry_price,
            "symbolic_validation": scored.coherence,
            "quantum_probability": 0.7,
        }

    def _to_ai_signal(self, scored: ScoredSignal) -> Any:  # type: ignore
        if not _EXECUTOR_AVAILABLE or TradingSignal is None:
            return self._fabricate_exec_signal(scored)
        try:
            return TradingSignal(  # type: ignore
                signal_id=scored.signal_id,
                symbol=scored.symbol,
                market_type=cast(Any, getattr(self._ai, "MarketType", None) or "stocks"),
                trade_type=cast(Any, scored.trade_type),
                confidence=0.75,
                risk_level=cast(Any, getattr(self._ai, "RiskLevel", None) or "moderate"),
                entry_price=scored.entry_price,
                target_price=scored.entry_price,
                stop_loss=scored.entry_price * 0.97,
                position_size=scored.position_size,
                reasoning="SE41 facade",
                symbolic_validation=scored.coherence,
                quantum_probability=0.7,
                consciousness_alignment=0.6,
            )
        except Exception:
            return self._fabricate_exec_signal(scored)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_trading_engine(**kwargs) -> TradingEngine:
    cfg_kwargs = {}
    for k in (
        "enable_ethos_gate",
        "min_coherence_allow",
        "risk_hold_threshold",
        "risk_deny_threshold",
        "paper_trading",
        "max_daily_risk",
        "max_position",
    ):
        if k in kwargs:
            cfg_kwargs[k] = kwargs[k]
    return TradingEngine(config=EngineConfig(**cfg_kwargs))


__all__ = [
    "TradingEngine",
    "create_trading_engine",
    "EngineConfig",
    "ScoredSignal",
]
