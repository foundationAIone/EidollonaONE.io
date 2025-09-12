"""trading_engine/pnl_calculator.py
===================================================================
EidollonaONE P&L Calculator — SE41 v4.1+ aligned

What this module provides
- Robust P&L entries (realized / unrealized) with holding period, returns.
- SE41-bound "profit manifestation" validator per entry (finite, bounded).
- Period summaries (intraday/daily/…/inception) with Sharpe/vol/WinRate/
  ProfitFactor and max drawdown.
- Quantum-aware performance analyzer to contextualize consistency/efficiency.

Safe fallbacks:
- If Position/PositionType or TradeType imports are missing, minimal stand-ins are used.
===================================================================
"""

from __future__ import annotations

import logging
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Optional: preserved export for engine-based importers
try:
    from trading_engine import TradingEngine  # noqa: F401

    __all__ = ["TradingEngine"]
except Exception:
    __all__ = []

# ---- SE41 v4.1 unified imports ------------------------------------
from symbolic_core.symbolic_equation41 import SymbolicEquation41
from trading.helpers.se41_trading_gate import se41_numeric  # numeric synthesis

# (We don't need se41_signals/ethos_decision for P&L computations.)

# ---- optional adjacent dependencies (graceful fallback) -----------
try:
    from trading_engine.ai_trade_executor import TradeType, MarketType, RiskLevel
except Exception:

    class TradeType(Enum):
        BUY = "buy"
        SELL = "sell"

    class MarketType(Enum):
        STOCKS = "stocks"
        FOREX = "forex"
        CRYPTO = "crypto"

    class RiskLevel(Enum):
        LOW = "low"
        MODERATE = "moderate"
        HIGH = "high"


try:
    from trading_engine.position_manager import Position, PositionType
except Exception:

    class PositionType(Enum):
        LONG = "long"
        SHORT = "short"

    @dataclass
    class Position:
        position_id: str
        symbol: str
        position_type: PositionType
        quantity: float
        entry_price: float
        entry_time: datetime
        status: Enum = field(default_factory=lambda: type("S", (), {"value": "open"})())
        fees_paid: float = 0.0


# --------------------------- enums & dataclasses ---------------------------


class PnLPeriod(Enum):
    INTRADAY = "intraday"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    INCEPTION = "inception"


class PnLType(Enum):
    REALIZED = "realized"
    UNREALIZED = "unrealized"
    TOTAL = "total"
    GROSS = "gross"
    NET = "net"


@dataclass
class PnLEntry:
    entry_id: str
    symbol: str
    trade_type: str
    position_id: Optional[str]
    quantity: float
    entry_price: float
    exit_price: Optional[float]

    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    fees: float = 0.0
    commission: float = 0.0

    entry_time: datetime = field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    calculation_time: datetime = field(default_factory=datetime.now)

    holding_period: timedelta = field(default_factory=lambda: timedelta(0))
    return_percentage: float = 0.0
    annualized_return: float = 0.0

    symbolic_coherence: float = 0.0
    quantum_probability: float = 0.0
    profit_manifestation_score: float = 0.0


@dataclass
class PnLSummary:
    period: PnLPeriod
    start_date: datetime
    end_date: datetime

    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    total_fees: float = 0.0
    total_commission: float = 0.0
    total_costs: float = 0.0

    total_return: float = 0.0
    return_percentage: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    volatility: float = 0.0

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0

    symbolic_coherence_avg: float = 0.0
    quantum_profit_score: float = 0.0
    consciousness_alignment: float = 0.0  # placeholder hook


# --------------------------- symbolic validator ---------------------------


class SymbolicProfitValidator:
    """SE41-bounded validator for P&L manifestation quality."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SymbolicProfitValidator")
        self._se41 = SymbolicEquation41()

    def validate_profit_manifestation(
        self, pnl_entry: PnLEntry, market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Computes a bounded numeric synthesis (0 < |v| < 1000) using profit ratio,
        fee efficiency, holding time, and market efficiency/volatility/trend.
        """
        try:
            notional = max(abs(pnl_entry.entry_price * pnl_entry.quantity), 1000.0)
            profit_ratio = (
                pnl_entry.realized_pnl + pnl_entry.unrealized_pnl
            ) / notional

            return_factor = min(abs(pnl_entry.return_percentage) / 100.0, 1.0)
            held_days = max(pnl_entry.holding_period.total_seconds() / 86400.0, 0.0)
            time_factor = min(held_days, 7.0) / 7.0

            # fees vs gains; bounded from above
            denom = max(
                abs(pnl_entry.realized_pnl) + abs(pnl_entry.unrealized_pnl), 100.0
            )
            fee_efficiency = 1.0 - min(pnl_entry.fees / denom, 1.0)

            # market context
            market_volatility = float(market_context.get("volatility", 0.2))
            market_trend = float(market_context.get("trend_strength", 0.5))
            market_efficiency = float(market_context.get("efficiency", 0.7))

            numeric = se41_numeric(
                M_t=market_efficiency,
                DNA_states=[
                    1.0,
                    abs(profit_ratio),
                    return_factor,
                    time_factor,
                    fee_efficiency,
                    market_trend,
                    1.1,
                ],
                harmonic_patterns=[
                    1.0,
                    1.2,
                    abs(profit_ratio),
                    return_factor,
                    time_factor,
                    fee_efficiency,
                    market_volatility,
                    market_trend,
                    market_efficiency,
                    1.3,
                ],
            )

            ok = (
                isinstance(numeric, (int, float))
                and math.isfinite(numeric)
                and 0.001 < abs(numeric) < 1000.0
            )
            if not ok:
                return {"valid": False, "manifestation_score": 0.0}

            score = min(abs(float(numeric)) / 65.0, 1.0)
            pnl_entry.profit_manifestation_score = score
            pnl_entry.symbolic_coherence = max(pnl_entry.symbolic_coherence, score)

            quality = self._assess_profit_quality(score, pnl_entry)
            self.logger.info(
                f"[SE41] profit validation {pnl_entry.symbol} score={score:.3f}"
            )

            return {
                "valid": True,
                "manifestation_score": score,
                "symbolic_result": numeric,
                "quality_assessment": quality,
                "profit_sustainability": score * market_efficiency,
                "optimal_profit": score >= 0.7,
                "validation_timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Profit validation failed: {e}")
            return {"valid": False, "manifestation_score": 0.0, "error": str(e)}

    def _assess_profit_quality(self, score: float, pnl_entry: PnLEntry) -> str:
        r = pnl_entry.return_percentage
        if score >= 0.9 and r >= 10.0:
            return "exceptional_manifestation"
        if score >= 0.8 and r >= 5.0:
            return "strong_manifestation"
        if score >= 0.7 and r >= 2.0:
            return "good_manifestation"
        if score >= 0.5:
            return "moderate_manifestation" if r >= 1.0 else "weak_manifestation"
        return "poor_manifestation"


# --------------------------- quantum analyzer ---------------------------


class QuantumPerformanceAnalyzer:
    """Light quantum-style aggregation for period performance."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.QuantumPerformanceAnalyzer")

    def analyze_quantum_performance(
        self, summary: PnLSummary, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            q_coh = random.uniform(0.8, 1.2)
            q_unc = random.uniform(0.9, 1.1)

            # derive base components
            return_quality = min(abs(summary.return_percentage) / 50.0, 1.0)
            consistency = 1.0 - min(summary.volatility / 0.5, 1.0)
            efficiency = summary.sharpe_ratio / 3.0 if summary.sharpe_ratio > 0 else 0.0
            drawdown_penalty = min(abs(summary.max_drawdown) / 0.3, 1.0)
            wr = summary.win_rate
            pf_score = (
                min(summary.profit_factor / 2.0, 1.0)
                if summary.profit_factor > 0
                else 0.0
            )

            base = (
                return_quality * 0.3
                + consistency * 0.2
                + efficiency * 0.2
                + wr * 0.15
                + pf_score * 0.15
            )
            risk_adj = base * (1.0 - 0.3 * drawdown_penalty)
            q_perf = min(risk_adj * q_coh * q_unc, 1.0)

            grade = (
                "exceptional"
                if q_perf >= 0.9
                else (
                    "excellent"
                    if q_perf >= 0.8
                    else (
                        "very_good"
                        if q_perf >= 0.7
                        else (
                            "good"
                            if q_perf >= 0.6
                            else (
                                "satisfactory"
                                if q_perf >= 0.5
                                else "below_average" if q_perf >= 0.4 else "poor"
                            )
                        )
                    )
                )
            )

            recs = self._recommend(summary, q_perf)
            self.logger.info(f"[Quantum] performance={grade} score={q_perf:.3f}")

            return {
                "quantum_performance_score": q_perf,
                "performance_grade": grade,
                "base_performance": base,
                "risk_adjusted_performance": risk_adj,
                "quantum_coherence": q_coh,
                "consistency_score": consistency,
                "efficiency_score": efficiency,
                "recommendations": recs,
                "analysis_timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Quantum performance analysis failed: {e}")
            return {"quantum_performance_score": 0.5, "performance_grade": "unknown"}

    def _recommend(self, s: PnLSummary, q_score: float) -> List[str]:
        out: List[str] = []
        if s.win_rate < 0.5:
            out += ["improve_trade_selection_criteria", "enhance_entry_signals"]
        if abs(s.max_drawdown) > 0.15:
            out += ["tighten_risk_management", "implement_position_sizing"]
        if s.sharpe_ratio < 1.0:
            out += ["optimize_risk_adjusted_returns"]
            if s.volatility > 0.3:
                out += ["reduce_portfolio_volatility"]
        if s.total_trades < 10:
            out += ["increase_trading_frequency"]
        elif s.total_trades > 1000:
            out += ["reduce_overtrading"]
        if (s.total_costs / max(abs(s.gross_pnl), 1000.0)) > 0.1:
            out += ["optimize_trading_costs", "review_broker_fees"]
        if q_score >= 0.8:
            out += ["maintain_current_strategy", "consider_capital_scaling"]
        elif q_score >= 0.6:
            out += ["fine_tune_existing_approach"]
        else:
            out += ["fundamental_strategy_review", "risk_assessment_required"]
        return out


# --------------------------- P&L calculator ---------------------------


class PnLCalculator:
    """
    EidollonaONE P&L Calculator (SE41 v4.1+)
    - Computes per-position PnL (realized/unrealized) + returns/annualization.
    - Validates each entry via SE41 "profit manifestation" (bounded, finite).
    - Aggregates period summaries and runs a quantum-style performance synthesis.
    """

    def __init__(self, calculator_directory: Optional[str] = None):
        self.logger = logging.getLogger(f"{__name__}.PnLCalculator")

        self.calculator_directory = Path(calculator_directory or "pnl_calculator_data")
        self.calculator_directory.mkdir(exist_ok=True)

        self.profit_validator = SymbolicProfitValidator()
        self.performance_analyzer = QuantumPerformanceAnalyzer()

        self.pnl_entries: Dict[str, PnLEntry] = {}
        self.pnl_summaries: Dict[str, PnLSummary] = {}
        self.daily_snapshots: Dict[str, Dict[str, Any]] = {}

        self.base_currency = "USD"
        self.calculation_precision = 4
        self.auto_calculate_interval = 300  # seconds

        self.logger.info("P&L Calculator v4.1+ initialized (symbolic✓ quantum✓)")

    async def calculate_position_pnl(
        self, position: Position, current_price: float, market_context: Dict[str, Any]
    ) -> PnLEntry:
        """Create a PnL entry for a position with current mark and validate it."""
        try:
            entry = PnLEntry(
                entry_id=f"pnl_{int(time.time())}_{uuid.uuid4().hex[:8]}",
                symbol=position.symbol,
                trade_type=str(position.position_type.value),
                position_id=getattr(position, "position_id", None),
                quantity=float(position.quantity),
                entry_price=float(position.entry_price),
                exit_price=(
                    current_price
                    if getattr(position.status, "value", "open") == "closed"
                    else None
                ),
                entry_time=position.entry_time,
                calculation_time=datetime.now(),
            )

            # holding period
            entry.holding_period = max(
                datetime.now() - position.entry_time, timedelta(0)
            )

            # pnl math
            if position.position_type == PositionType.LONG:
                entry.unrealized_pnl = (
                    current_price - position.entry_price
                ) * position.quantity
            else:  # SHORT
                entry.unrealized_pnl = (
                    position.entry_price - current_price
                ) * position.quantity

            if getattr(position.status, "value", "open") == "closed":
                entry.realized_pnl = entry.unrealized_pnl
                entry.unrealized_pnl = 0.0
                entry.exit_time = datetime.now()

            entry.fees = float(getattr(position, "fees_paid", 0.0))
            entry.commission = entry.fees * 0.5  # crude split

            # returns
            cost_basis = max(abs(position.entry_price * position.quantity), 1e-9)
            total_pnl = entry.realized_pnl + entry.unrealized_pnl
            entry.return_percentage = (total_pnl / cost_basis) * 100.0

            days_held = max(entry.holding_period.total_seconds() / 86400.0, 0.0)
            if days_held > 0:
                daily_ret = entry.return_percentage / days_held
                entry.annualized_return = daily_ret * 365.0

            # SE41 validation
            _ = self.profit_validator.validate_profit_manifestation(
                entry, market_context
            )

            self.pnl_entries[entry.entry_id] = entry
            self.logger.info(
                f"[PnL] {position.symbol} pnl=${total_pnl:.2f} ({entry.return_percentage:.2f}%)"
            )
            return entry

        except Exception as e:
            self.logger.error(f"Position P&L calculation failed: {e}")
            raise

    async def calculate_period_summary(
        self,
        period: PnLPeriod,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> PnLSummary:
        """Aggregate entries over [start_date, end_date] into a summary and analyze."""
        try:
            if end_date is None:
                end_date = datetime.now()
            if start_date is None:
                start_date = self._period_start(period, end_date)

            entries = [
                e
                for e in self.pnl_entries.values()
                if start_date <= e.calculation_time <= end_date
            ]

            summary = PnLSummary(
                period=period, start_date=start_date, end_date=end_date
            )
            if not entries:
                self.pnl_summaries[self._summary_key(period, start_date, end_date)] = (
                    summary
                )
                return summary

            summary.realized_pnl = sum(e.realized_pnl for e in entries)
            summary.unrealized_pnl = sum(e.unrealized_pnl for e in entries)
            summary.total_fees = sum(e.fees for e in entries)
            summary.total_commission = sum(e.commission for e in entries)
            summary.total_costs = summary.total_fees + summary.total_commission
            summary.gross_pnl = summary.realized_pnl + summary.unrealized_pnl
            summary.net_pnl = summary.gross_pnl - summary.total_costs

            await self._compute_perf(summary, entries)

            # quantum analysis
            perf_ctx = {"period": period.value, "entries_count": len(entries)}
            q = self.performance_analyzer.analyze_quantum_performance(summary, perf_ctx)
            summary.quantum_profit_score = float(
                q.get("quantum_performance_score", 0.5)
            )

            self.pnl_summaries[self._summary_key(period, start_date, end_date)] = (
                summary
            )
            self.logger.info(
                f"[PnL] {period.value} net=${summary.net_pnl:.2f} ({summary.return_percentage:.2f}%)"
            )
            return summary

        except Exception as e:
            self.logger.error(f"Period summary calculation failed: {e}")
            raise

    # --------------------------- helpers ---------------------------

    def _period_start(self, period: PnLPeriod, end_date: datetime) -> datetime:
        if period == PnLPeriod.INTRADAY:
            return end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == PnLPeriod.DAILY:
            return end_date - timedelta(days=1)
        if period == PnLPeriod.WEEKLY:
            return end_date - timedelta(weeks=1)
        if period == PnLPeriod.MONTHLY:
            return end_date - timedelta(days=30)
        if period == PnLPeriod.QUARTERLY:
            return end_date - timedelta(days=90)
        if period == PnLPeriod.YEARLY:
            return end_date - timedelta(days=365)
        return datetime(2024, 1, 1)  # inception default

    async def _compute_perf(self, s: PnLSummary, entries: List[PnLEntry]) -> None:
        # trades
        closed = [e for e in entries if e.realized_pnl != 0]
        s.total_trades = len(closed)
        if closed:
            wins = [e for e in closed if e.realized_pnl > 0]
            loss = [e for e in closed if e.realized_pnl < 0]
            s.winning_trades = len(wins)
            s.losing_trades = len(loss)
            s.win_rate = s.winning_trades / max(s.total_trades, 1)

            if wins:
                s.average_win = sum(e.realized_pnl for e in wins) / len(wins)
            if loss:
                s.average_loss = sum(abs(e.realized_pnl) for e in loss) / len(loss)

            total_wins = sum(e.realized_pnl for e in wins)
            total_losses = sum(abs(e.realized_pnl) for e in loss)
            if total_losses > 0:
                s.profit_factor = total_wins / total_losses

        # returns vs notional
        total_capital = sum(max(abs(e.entry_price * e.quantity), 1e-9) for e in entries)
        if total_capital > 0:
            s.total_return = s.net_pnl
            s.return_percentage = (s.net_pnl / total_capital) * 100.0

        # vol & sharpe
        if len(closed) > 1:
            returns = [e.return_percentage for e in closed]
            mu = sum(returns) / len(returns)
            var = sum((r - mu) ** 2 for r in returns) / len(returns)
            s.volatility = math.sqrt(max(var, 0.0))
            if s.volatility > 0:
                s.sharpe_ratio = mu / s.volatility

        # max drawdown (cumulative pnl path)
        cum, peak, max_dd = 0.0, 0.0, 0.0
        for e in sorted(entries, key=lambda x: x.calculation_time):
            cum += e.realized_pnl + e.unrealized_pnl
            if cum > peak:
                peak = cum
            dd = (peak - cum) / max(peak, 1.0)
            if dd > max_dd:
                max_dd = dd
        s.max_drawdown = max_dd

        # symbolic coherence average
        s.symbolic_coherence_avg = sum(e.symbolic_coherence for e in entries) / max(
            len(entries), 1
        )

    def _summary_key(self, p: PnLPeriod, s: datetime, e: datetime) -> str:
        return f"{p.value}_{s.strftime('%Y%m%d')}_{e.strftime('%Y%m%d')}"


# --------------------------- factory & smoke ---------------------------


def create_pnl_calculator(**kwargs) -> PnLCalculator:
    return PnLCalculator(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 70)
    print("EidollonaONE P&L Calculator v4.1+ — bounded • coherent • auditable")
    print("=" * 70)
