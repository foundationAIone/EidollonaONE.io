from __future__ import annotations

from trading_engine import TradingEngine

__all__ = ["TradingEngine"]

# Trading Engine Module (SE41 v4.1+)
# Unified import & helper stanza injected by rewrite_trading_engine_v41.ps1
from symbolic_core.symbolic_equation41 import SymbolicEquation41
from trading.helpers.se41_trading_gate import (
    ethos_decision_envelope,
    se41_numeric,
)

# Standard library
import logging
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

"""
🎯 EidollonaONE Strategy Selector v4.1+

Advanced strategy selection with:
  • SE41 bounded symbolic merit (no NaNs/Inf)
  • Ethos gate (Authenticity / Integrity / Responsibility / Enrichment)
  • Regime-aware recommendations
  • Quantum evolution hooks

Purpose: pick & adapt the best strategies for the *current* regime and portfolio posture.
"""

# --- optional cross-module types ------------------------------------------------
# Use local enums to ensure consistent type identity for analyzers
class MarketType(Enum):
    STOCKS = "stocks"
    FOREX = "forex"
    CRYPTO = "crypto"
    FUTURES = "futures"


class RiskLevel(Enum):
    MINIMAL = 0
    LOW = 1
    MODERATE = 2
    HIGH = 3
    EXTREME = 4


# --- strategy model ------------------------------------------------------------


class StrategyType(Enum):
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    ARBITRAGE = "arbitrage"
    PAIRS_TRADING = "pairs_trading"
    BREAKOUT = "breakout"
    SCALPING = "scalping"
    SWING_TRADING = "swing_trading"
    GRID_TRADING = "grid_trading"
    MARTINGALE = "martingale"
    SYMBOLIC_ADAPTIVE = "symbolic_adaptive"
    QUANTUM_ENHANCED = "quantum_enhanced"
    CONSCIOUSNESS_GUIDED = "consciousness_guided"


class MarketRegime(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    EUPHORIA = "euphoria"


class StrategyStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    OPTIMIZING = "optimizing"
    DISABLED = "disabled"


@dataclass
class TradingStrategy:
    strategy_id: str
    name: str
    strategy_type: StrategyType
    description: str

    # controls
    parameters: Dict[str, Any] = field(default_factory=dict)
    risk_profile: RiskLevel = RiskLevel.MODERATE
    time_horizon: str = "medium"  # short, medium, long
    market_types: List[MarketType] = field(default_factory=list)

    # telemetry
    status: StrategyStatus = StrategyStatus.INACTIVE
    total_trades: int = 0
    profitable_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0

    # symbolic/quantum
    symbolic_coherence: float = 0.0
    quantum_probability: float = 0.0
    consciousness_alignment: float = 0.0
    adaptation_score: float = 0.0

    created_time: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)
    usage_count: int = 0

    preferred_regimes: List[MarketRegime] = field(default_factory=list)
    regime_performance: Dict[str, float] = field(default_factory=dict)


@dataclass
class StrategyPerformance:
    strategy_id: str
    evaluation_period: str
    start_date: datetime
    end_date: datetime
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    calmar_ratio: float = 0.0
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_trade: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    information_ratio: float = 0.0
    treynor_ratio: float = 0.0
    jensen_alpha: float = 0.0
    beta: float = 0.0
    symbolic_effectiveness: float = 0.0
    quantum_optimization_score: float = 0.0
    consciousness_resonance: float = 0.0


# --- optimizer ----------------------------------------------------------------


class SymbolicStrategyOptimizer:
    """
    SE41 strategy optimizer:
      merit = bounded synthesis of market, portfolio, and strategy health → [0..1]
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SymbolicStrategyOptimizer")
        self._se41 = SymbolicEquation41()

    def _risk_factor(self, risk: RiskLevel) -> float:
        table = {
            RiskLevel.MINIMAL: 0.90,
            RiskLevel.LOW: 0.80,
            RiskLevel.MODERATE: 0.60,
            RiskLevel.HIGH: 0.40,
            RiskLevel.EXTREME: 0.20,
        }
        return table.get(risk, 0.60)

    def _recency_factor(self, strategy: TradingStrategy) -> float:
        """higher if used within ~a week, slightly lower if used too recently"""
        if not strategy.last_used:
            return 0.55
        days = (datetime.now() - strategy.last_used).total_seconds() / 86400
        if days < 1:
            return 0.70
        if days < 7:
            return 0.90
        if days < 30:
            return 0.80
        return 0.60

    def _regime(self, mc: Dict[str, Any]) -> MarketRegime:
        vol = mc.get("volatility", 0.2)
        trend = mc.get("trend_strength", 0.5)
        mom = mc.get("momentum", 0.0)
        if vol > 0.4:
            if abs(mom) > 0.1:
                return MarketRegime.CRISIS if mom < 0 else MarketRegime.EUPHORIA
            return MarketRegime.HIGH_VOLATILITY
        if vol < 0.15:
            return MarketRegime.LOW_VOLATILITY
        if trend > 0.7:
            return MarketRegime.TRENDING_UP if mom > 0 else MarketRegime.TRENDING_DOWN
        return MarketRegime.SIDEWAYS

    def optimize(
        self,
        strategies: List[TradingStrategy],
        market_conditions: Dict[str, Any],
        portfolio_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Returns: {optimal_strategy_id, optimization_score, strategy_scores, recommendations, market_regime, ethos}
        """
        try:
            # Note: vol is inferred within _regime; avoid duplicate local to keep analyzers clean
            trend = float(market_conditions.get("trend_strength", 0.50))
            liquidity = float(market_conditions.get("liquidity", 0.70))
            momentum = float(market_conditions.get("momentum", 0.00))
            breadth = float(market_conditions.get("breadth", 0.50))

            p_risk = float(portfolio_context.get("risk_level", 0.50))
            p_value = float(portfolio_context.get("total_value", 100_000))
            exposure = float(portfolio_context.get("exposure", 0.50))

            regime = self._regime(market_conditions)
            scores: Dict[str, float] = {}

            for s in strategies:
                if s.status not in (StrategyStatus.ACTIVE, StrategyStatus.TESTING):
                    continue

                risk_f = self._risk_factor(s.risk_profile)
                perf_f = max(0.0, min(s.win_rate, 1.0))
                recency_f = self._recency_factor(s)
                usage_f = max(0.0, min(s.usage_count / 100.0, 1.0))
                stress_f = max(0.0, min((abs(s.max_drawdown) / 0.3), 1.0))
                pnl_f = max(0.0, min(s.total_pnl / max(p_value, 1.0), 1.0))

                # Symbolic bounded synthesis
                numeric = se41_numeric(
                    M_t=max(
                        0.05, (1.0 - p_risk) * 0.5 + liquidity * 0.3 + breadth * 0.2
                    ),
                    DNA_states=[
                        1.0,
                        perf_f,
                        risk_f,
                        recency_f,
                        1.0 - stress_f,
                        pnl_f,
                        1.05,
                    ],
                    harmonic_patterns=[
                        1.0,
                        1.2,
                        perf_f,
                        risk_f,
                        recency_f,
                        (1.0 - p_risk),
                        liquidity,
                        momentum,
                        trend,
                        exposure,
                        usage_f,
                        1.15,
                    ],
                )

                ok = (
                    isinstance(numeric, (int, float))
                    and math.isfinite(numeric)
                    and 0.001 < abs(numeric) < 1000.0
                )
                merit = min(abs(float(numeric)) / 70.0, 1.0) if ok else 0.3
                s.symbolic_coherence = merit
                scores[s.strategy_id] = merit

            if not scores:
                return {
                    "optimal_strategy_id": None,
                    "optimization_score": 0.0,
                    "strategy_scores": {},
                }

            # Ethos gate over a compact signal packet (or call se41_signals for a richer set)
            best_id = max(scores, key=lambda k: scores[k])
            best_merit = scores[best_id]
            ethos_in = {
                "coherence": best_merit,
                "risk": p_risk,
                "impetus": best_merit * max(0.0, min(trend, 1.0)),
                "ethos": {
                    "authenticity": 0.88,
                    "integrity": 0.90,
                    "responsibility": max(0.0, min(1.0 - p_risk, 1.0)),
                    "enrichment": max(0.0, min(liquidity * breadth, 1.0)),
                },
                "explain": "strategy_selector",
            }
            ethos = ethos_decision_envelope(ethos_in)

            recs = self._recommendations(
                scores, market_conditions, portfolio_context, regime
            )
            return {
                "optimal_strategy_id": best_id,
                "optimization_score": round(best_merit, 4),
                "strategy_scores": {k: round(v, 4) for k, v in scores.items()},
                "recommendations": recs,
                "market_regime": regime.value,
                "ethos": ethos,
                "optimization_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Strategy optimization failed: {e}")
            return {
                "optimal_strategy_id": None,
                "optimization_score": 0.0,
                "error": str(e),
            }

    def _recommendations(
        self,
        scores: Dict[str, float],
        mc: Dict[str, Any],
        pc: Dict[str, Any],
        regime: MarketRegime,
    ) -> List[str]:
        recs: List[str] = []
        # Read but don't retain locals to avoid analyzer unused warnings
        _ = (
            mc.get("volatility", 0.2),
            mc.get("trend_strength", 0.5),
            mc.get("momentum", 0.0),
        )

        if regime == MarketRegime.TRENDING_UP:
            recs += ["favor_momentum_strategies", "consider_trend_following"]
        elif regime == MarketRegime.TRENDING_DOWN:
            recs += ["consider_short_strategies", "implement_defensive_positions"]
        elif regime == MarketRegime.SIDEWAYS:
            recs += ["favor_mean_reversion", "consider_range_trading"]
        elif regime == MarketRegime.HIGH_VOLATILITY:
            recs += ["reduce_position_sizes", "increase_stop_losses"]
        elif regime == MarketRegime.LOW_VOLATILITY:
            recs += ["consider_breakout_strategies", "increase_position_sizes"]
        elif regime in (MarketRegime.CRISIS,):
            recs += ["capital_preservation_mode"]

        # portfolio risk prompts
        if pc.get("risk_level", 0.5) > 0.7:
            recs += ["reduce_strategy_risk", "diversify_strategies"]

        # top2 closeness → consider blend
        top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
        if len(top) == 2 and (top[0][1] - top[1][1]) < 0.1:
            recs.append("consider_strategy_combination")
        return recs


# --- evolution ----------------------------------------------------------------


class QuantumStrategyEvolution:
    """Quantum-enhanced parameter evolution with bounds & quality scoring."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.QuantumStrategyEvolution")
        self.evolution_history: List[Dict[str, Any]] = []

    def evolve(
        self, strategy: TradingStrategy, perf: Dict[str, Any], feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            q_unc = random.uniform(0.85, 1.15)
            coh = random.uniform(0.70, 1.00)
            perf_k = float(perf.get("recent_performance", 0.5))
            vol_k = float(perf.get("volatility_adaptation", 0.5))
            align = float(feedback.get("alignment_score", 0.5))

            current = strategy.parameters.copy()
            evolved = {}
            mult_base = 0.5 + 0.5 * perf_k

            def bound(name: str, val: float, orig: float) -> float:
                bounds = {
                    "risk_threshold": (0.01, 0.50),
                    "stop_loss": (0.005, 0.20),
                    "take_profit": (0.01, 1.00),
                    "position_size": (0.1, 10.0),
                    "leverage": (1.0, 5.0),
                    "entry_threshold": (0.1, 2.0),
                    "exit_threshold": (0.1, 2.0),
                }
                if name in bounds:
                    lo, hi = bounds[name]
                    return round(max(lo, min(hi, val)), 6)
                # generic ±50%
                lo, hi = orig * 0.5, orig * 1.5
                return round(max(lo, min(hi, val)), 6)

            for k, v in current.items():
                if not isinstance(v, (int, float)):
                    evolved[k] = v
                    continue
                evo = v * q_unc * coh * mult_base
                if k in ("risk_threshold", "stop_loss", "take_profit"):
                    evo *= 1.0 + (vol_k - 0.5) * 0.2
                elif k in ("position_size", "leverage"):
                    evo *= 1.0 + (perf_k - 0.5) * 0.3
                elif k in ("entry_threshold", "exit_threshold"):
                    evo *= 1.0 + (align - 0.5) * 0.25
                evolved[k] = bound(k, evo, v)

            # quality
            changes = 0
            total = 0
            for k, v in current.items():
                if isinstance(v, (int, float)):
                    total += 1
                    if v != 0 and abs(evolved[k] - v) / abs(v) > 0.05:
                        changes += 1
            change_ratio = changes / max(total, 1)
            if 0.3 <= change_ratio <= 0.7 and perf_k > 0.6:
                quality = 0.8 + change_ratio * 0.2
            elif change_ratio < 0.3:
                quality = 0.6 + change_ratio
            else:
                quality = 0.7 - (change_ratio - 0.7) * 0.5
            quality = min(quality * (0.5 + perf_k * 0.5), 1.0)

            strategy.adaptation_score = quality * coh
            strategy.quantum_probability = q_unc * coh

            rec = {
                "strategy_id": strategy.strategy_id,
                "evolution_time": datetime.now().isoformat(),
                "original_params": current,
                "evolved_params": evolved,
                "evolution_quality": quality,
                "quantum_factor": q_unc,
            }
            self.evolution_history.append(rec)
            return {
                "evolved_parameters": evolved,
                "evolution_quality": quality,
                "quantum_uncertainty": q_unc,
                "evolution_coherence": coh,
            }
        except Exception as e:
            self.logger.error(f"Strategy evolution failed: {e}")
            return {"evolved_parameters": strategy.parameters, "evolution_quality": 0.0}


# --- selector orchestration ---------------------------------------------------


class StrategySelector:
    """
    Orchestrates strategy review → selection → activation,
    with SE41 merit + Ethos gate and optional quantum evolution.
    """

    def __init__(self, selector_directory: Optional[str] = None):
        self.logger = logging.getLogger(f"{__name__}.StrategySelector")
        self.selector_directory = Path(selector_directory or "strategy_selector_data")
        self.selector_directory.mkdir(exist_ok=True)

        self.optimizer = SymbolicStrategyOptimizer()
        self.evolution_engine = QuantumStrategyEvolution()

        self.strategies: Dict[str, TradingStrategy] = {}
        self.strategy_performance: Dict[str, StrategyPerformance] = {}
        self.active_strategy_id: Optional[str] = None

        self.max_strategies = 20
        self.selection_interval = 3600  # seconds
        self.evolution_threshold = 0.10  # performance delta to trigger evolution

        self._init_defaults()
        self.logger.info(
            "Strategy Selector v4.1+ initialized | SE41 merit + Ethos gating ready"
        )

    def _init_defaults(self) -> None:
        try:
            defaults = [
                dict(
                    name="Trend Following Momentum",
                    strategy_type=StrategyType.TREND_FOLLOWING,
                    description="Follows strong trends with momentum confirmation.",
                    parameters=dict(
                        trend_threshold=0.7,
                        momentum_window=20,
                        stop_loss=0.05,
                        take_profit=0.15,
                        position_size=1.0,
                    ),
                    risk_profile=RiskLevel.MODERATE,
                    time_horizon="medium",
                    market_types=[
                        MarketType.STOCKS,
                        MarketType.FOREX,
                        MarketType.CRYPTO,
                    ],
                    preferred_regimes=[
                        MarketRegime.TRENDING_UP,
                        MarketRegime.TRENDING_DOWN,
                    ],
                ),
                dict(
                    name="Mean Reversion Scalper",
                    strategy_type=StrategyType.MEAN_REVERSION,
                    description="Exploits short-term mean reversion.",
                    parameters=dict(
                        reversion_threshold=2.0,
                        lookback_period=10,
                        stop_loss=0.02,
                        take_profit=0.05,
                        position_size=0.5,
                    ),
                    risk_profile=RiskLevel.HIGH,
                    time_horizon="short",
                    market_types=[MarketType.STOCKS, MarketType.FOREX],
                    preferred_regimes=[
                        MarketRegime.SIDEWAYS,
                        MarketRegime.LOW_VOLATILITY,
                    ],
                ),
                dict(
                    name="Breakout Hunter",
                    strategy_type=StrategyType.BREAKOUT,
                    description="Captures price breakouts from consolidation.",
                    parameters=dict(
                        breakout_threshold=1.5,
                        consolidation_period=15,
                        stop_loss=0.03,
                        take_profit=0.12,
                        position_size=0.8,
                    ),
                    risk_profile=RiskLevel.MODERATE,
                    time_horizon="medium",
                    market_types=[MarketType.STOCKS, MarketType.CRYPTO],
                    preferred_regimes=[
                        MarketRegime.LOW_VOLATILITY,
                        MarketRegime.RECOVERY,
                    ],
                ),
                dict(
                    name="Symbolic Adaptive AI",
                    strategy_type=StrategyType.SYMBOLIC_ADAPTIVE,
                    description="AI strategy guided by SE41 signals.",
                    parameters=dict(
                        adaptation_rate=0.1,
                        symbolic_threshold=0.7,
                        quantum_factor=0.8,
                        stop_loss=0.04,
                        take_profit=0.10,
                        position_size=1.2,
                    ),
                    risk_profile=RiskLevel.LOW,
                    time_horizon="medium",
                    market_types=[
                        MarketType.STOCKS,
                        MarketType.FOREX,
                        MarketType.CRYPTO,
                        MarketType.FUTURES,
                    ],
                    preferred_regimes=list(MarketRegime),
                ),
            ]
            from typing import cast, Dict as _Dict, Any as _Any, List as _List

            for cfg in defaults:
                sid = f"strategy_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                s = TradingStrategy(
                    strategy_id=sid,
                    name=str(cfg["name"]),
                    strategy_type=cast(StrategyType, cfg["strategy_type"]),
                    description=str(cfg["description"]),
                    parameters=cast(_Dict[str, _Any], cfg["parameters"]),
                    risk_profile=cast(RiskLevel, cfg["risk_profile"]),
                    time_horizon=str(cfg["time_horizon"]),
                    market_types=cast(_List[MarketType], cfg["market_types"]),
                    preferred_regimes=cast(
                        _List[MarketRegime], cfg["preferred_regimes"]
                    ),
                    status=StrategyStatus.ACTIVE,
                )
                self.strategies[sid] = s
        except Exception as e:
            self.logger.error(f"Default strategy init failed: {e}")

    # ---------- public API ----------

    def review_selection(
        self, market_conditions: Dict[str, Any], portfolio_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute optimal strategy + recommendations + ethos decision.
        """
        res = self.optimizer.optimize(
            list(self.strategies.values()), market_conditions, portfolio_context
        )
        return res

    def activate_optimal(
        self, market_conditions: Dict[str, Any], portfolio_context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Picks optimal, applies Ethos allow/hold/deny, and sets active_strategy_id.
        Returns the activated strategy_id (or None if held/denied).
        """
        res = self.review_selection(market_conditions, portfolio_context)
        sid = res.get("optimal_strategy_id")
        ethos = (res.get("ethos") or {}).get("decision", "hold")
        if not sid:
            self.logger.info("No eligible strategies to activate.")
            return None
        if ethos != "allow":
            self.logger.info(f"Ethos gate: {ethos}. Strategy held: {sid}")
            return None

        self.active_strategy_id = sid
        s = self.strategies.get(sid)
        if s:
            s.last_used = datetime.now()
            s.usage_count += 1
        self.logger.info(
            f"Activated strategy: {sid} (merit={res.get('optimization_score')})"
        )
        return sid

    def update_performance(
        self,
        strategy_id: str,
        total_return: float,
        win_rate: float,
        sharpe: float,
        max_dd: float,
    ) -> bool:
        """
        Minimal telemetry updater from your backtester/runner for future selections.
        """
        s = self.strategies.get(strategy_id)
        if not s:
            return False
        s.total_pnl += total_return
        s.win_rate = max(0.0, min(win_rate, 1.0))
        s.sharpe_ratio = sharpe
        s.max_drawdown = max_dd
        s.last_updated = datetime.now()
        return True


# --- factory & smoke ----------------------------------------------------------
def create_strategy_selector(**kwargs) -> StrategySelector:
    return StrategySelector(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    selector = create_strategy_selector()
    market = {
        "volatility": 0.22,
        "trend_strength": 0.68,
        "liquidity": 0.74,
        "momentum": 0.12,
        "breadth": 0.58,
    }
    portfolio = {"risk_level": 0.42, "total_value": 250_000, "exposure": 0.55}

    review = selector.review_selection(market, portfolio)
    print(
        "Review:",
        {
            k: review[k]
            for k in [
                "optimal_strategy_id",
                "optimization_score",
                "market_regime",
                "ethos",
            ]
        },
    )

    activated = selector.activate_optimal(market, portfolio)
    print("Activated:", activated)

# --- Development Notes (TL;DR) ---
# Replaced placeholder calls with real SE41 numeric synthesis: se41_numeric(M_t=..., DNA_states=..., harmonic_patterns=...) -> bounded merit.
# Added Ethos gating to top choice before activation.
# Regime detection & recommendations upgraded and decoupled.
# Clean, auditable API (review_selection, activate_optimal, update_performance) for services/UI.
