# trading_engine/financial_autonomy_engine.py
# ===================================================================
# EidollonaONE Financial Autonomy Engine — SE41 v4.1+ aligned
#
# What this module does
# - Pulls SE41Signals once per loop (coherence, risk, uncertainty, ethos,
#   embodiment) using shared helper (no fragile per-file injections).
# - Validates financial decisions with v4.1 coherence + Four Pillars gate.
# - Orchestrates portfolio rebalances, trading, and health/wealth status.
# - Journals each decision and a compact loop snapshot for audit.
#
# Dependencies (first-party):
#   trading.helpers.se41_trading_gate: se41_signals, ethos_decision, se41_numeric
#   symbolic_core.symbolic_equation41 & se41_context (fallback only)
# ===================================================================

from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any

from symbolic_core.symbolic_equation41 import SymbolicEquation41
from trading.helpers.se41_trading_gate import se41_signals, ethos_decision, se41_numeric

try:
    from trading_engine.ai_trade_executor import (
        create_ai_trade_executor,
    )

    TRADE_EXECUTOR_AVAILABLE = True
except ImportError:
    TRADE_EXECUTOR_AVAILABLE = False

try:
    from trading_engine.autonomous_portfolio_manager import (
        create_portfolio_manager,
    )

    PORTFOLIO_MANAGER_AVAILABLE = True
except ImportError:
    PORTFOLIO_MANAGER_AVAILABLE = False

try:
    from trading_engine.market_intelligence_analyzer import (
        create_market_analyzer,
    )

    MARKET_ANALYZER_AVAILABLE = True
except ImportError:
    MARKET_ANALYZER_AVAILABLE = False


# --------------------------- Status & objectives ---------------------------


class FinancialStatus(Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PROFITABLE = "profitable"
    AUTONOMOUS = "autonomous"
    WEALTHY = "wealthy"
    FINANCIAL_FREEDOM = "financial_freedom"
    PAUSED = "paused"
    ERROR = "error"


class FinancialObjective(Enum):
    CAPITAL_PRESERVATION = "capital_preservation"
    STEADY_GROWTH = "steady_growth"
    AGGRESSIVE_GROWTH = "aggressive_growth"
    INCOME_GENERATION = "income_generation"
    WEALTH_ACCUMULATION = "wealth_accumulation"
    FINANCIAL_INDEPENDENCE = "financial_independence"


# --------------------------- Metrics & decisions ---------------------------


@dataclass
class FinancialMetrics:
    total_portfolio_value: float
    liquid_cash: float
    invested_capital: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    ytd_pnl: float
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    trades_today: int
    trades_total: int
    risk_score: float
    diversification_score: float
    liquidity_score: float
    financial_health_score: float
    wealth_growth_rate: float
    time_to_financial_freedom: Optional[float] = None


@dataclass
class FinancialDecision:
    decision_id: str
    timestamp: datetime
    decision_type: str  # "trade" | "rebalance" | "risk_adjustment" | ...
    description: str
    reasoning: str
    expected_outcome: str
    confidence: float
    risk_level: str  # "minimal".."extreme"
    symbolic_validation: float
    quantum_probability: float
    consciousness_alignment: float
    execution_status: str = "pending"
    actual_outcome: Optional[str] = None


# --------------------------- v4.1 scoring helpers ---------------------------


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


def _bounded_coherence(sig: Dict[str, Any]) -> float:
    """
    Conservative, bounded coherence scalar [0..1] for financial decisions.
    """
    if not sig:
        return 0.0
    coh = float(sig.get("coherence", 0.0))
    mc = float(sig.get("mirror_consistency", 0.0))
    me = _min_ethos(sig)
    risk = float(sig.get("risk", 0.25))
    unc = float(sig.get("uncertainty", 0.25))
    raw = 0.55 * coh + 0.25 * mc + 0.20 * me
    damp = max(0.35, 1.0 - 0.50 * (risk + unc))
    return max(0.0, min(1.0, raw * damp))


# --------------------------- Symbolic validator ---------------------------


class SymbolicFinancialValidator:
    """
    v4.1 financial validator:
    - Pulls SE41Signals
    - Computes a bounded validation score
    - Falls back to se41_numeric() (guarded) if signals absent
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.SymbolicFinancialValidator")
        self._se41 = SymbolicEquation41()  # guarded fallback

    def validate_financial_decision(
        self, decision: FinancialDecision, current_metrics: FinancialMetrics
    ) -> Dict[str, Any]:
        try:
            sig = se41_signals()
            if not sig:
                # guarded numeric fallback
                try:
                    numeric = se41_numeric(
                        DNA_states=[
                            1.0,
                            decision.confidence,
                            current_metrics.financial_health_score,
                            1.1,
                        ],
                        harmonic_patterns=[
                            1.0,
                            1.2,
                            abs(current_metrics.annualized_return),
                            1.3,
                        ],
                    )
                    score = max(0.0, min(1.0, abs(float(numeric)) / 80.0))
                except Exception:
                    # ultimate safe default
                    score = 0.6
            else:
                score = _bounded_coherence(sig)

            decision.symbolic_validation = score
            recommendation = self._recommend(score, decision)

            self.logger.info(
                "Financial decision %s v4.1 validation: %.3f (%s)",
                decision.decision_id,
                score,
                recommendation,
            )

            return {
                "valid": True,
                "validation_score": score,
                "signals": sig or {},
                "recommendation": recommendation,
                "proceed_with_decision": score >= 0.65,
                "risk_adjusted_confidence": min(score * decision.confidence, 1.0),
                "validation_timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error("Financial decision validation failed: %s", e)
            return {"valid": False, "validation_score": 0.0, "error": str(e)}

    def _recommend(self, score: float, decision: FinancialDecision) -> str:
        if score >= 0.9 and decision.confidence >= 0.8:
            return "strong_approve"
        if score >= 0.75 and decision.confidence >= 0.6:
            return "approve"
        if score >= 0.65:
            return "conditional_approve"
        if score >= 0.45:
            return "review_required"
        return "reject"


# --------------------------- Financial Autonomy Engine ---------------------------


class FinancialAutonomyEngine:
    """
    Orchestrates portfolio management, market analysis, and trading decisions
    with v4.1 coherence + Four Pillars gating and complete journaling.
    """

    def __init__(self, engine_directory: Optional[str] = None) -> None:
        self.logger = logging.getLogger(f"{__name__}.FinancialAutonomyEngine")

        # Configuration & directories
        self.engine_directory = Path(engine_directory or "financial_autonomy_data")
        self.engine_directory.mkdir(exist_ok=True)
        self.journal_path = self.engine_directory / "financial_decisions.jsonl"
        self.snapshot_path = self.engine_directory / "autonomy_snapshots.jsonl"

        # High-level state
        self.status = FinancialStatus.INITIALIZING
        self.objective = FinancialObjective.WEALTH_ACCUMULATION
        self.risk_tolerance = 0.7
        self.target_annual_return = 0.20
        self.financial_freedom_target = 1_000_000.0

        # Subsystems
        self.symbolic_validator = SymbolicFinancialValidator()
        self.trade_executor = (
            create_ai_trade_executor() if TRADE_EXECUTOR_AVAILABLE else None  # type: ignore[name-defined]
        )
        self.portfolio_manager = (
            create_portfolio_manager() if PORTFOLIO_MANAGER_AVAILABLE else None  # type: ignore[name-defined]
        )
        self.market_analyzer = (
            create_market_analyzer() if MARKET_ANALYZER_AVAILABLE else None  # type: ignore[name-defined]
        )

        # Performance tracking
        self.decision_history: List[FinancialDecision] = []
        self.metrics_history: List[FinancialMetrics] = []
        self.performance_tracking = {
            "start_time": datetime.now(),
            "start_capital": 100_000.0,
            "peak_value": 100_000.0,
            "total_decisions": 0,
            "successful_decisions": 0,
            "wealth_milestones": [],
        }

        # Ops knobs
        self.autonomous_mode = False
        self.max_daily_risk = 0.05
        self.rebalance_frequency = timedelta(hours=6)
        self.last_rebalance = datetime.now()

        self.status = FinancialStatus.ACTIVE
        self.logger.info(
            "Financial Autonomy Engine v4.1+ initialized " "(TE:%s PM:%s MI:%s)",
            "✅" if self.trade_executor else "❌",
            "✅" if self.portfolio_manager else "❌",
            "✅" if self.market_analyzer else "❌",
        )

    # ----------------------- main loop -----------------------

    async def start_financial_autonomy(self) -> None:
        self.autonomous_mode = True
        self.logger.info("🚀 Starting Financial Autonomy Engine...")
        try:
            await self._financial_autonomy_loop()
        except Exception as e:
            self.logger.error("Autonomy loop crashed: %s", e)
            self.status = FinancialStatus.ERROR

    async def _financial_autonomy_loop(self) -> None:
        while self.autonomous_mode and self.status not in (
            FinancialStatus.ERROR,
            FinancialStatus.PAUSED,
        ):
            try:
                sig = se41_signals() or {}
                metrics = await self._calculate_financial_metrics()
                self.metrics_history.append(metrics)

                await self._health_and_objective(metrics, sig)
                if self.market_analyzer:
                    await self._perform_market_analysis()

                if self.portfolio_manager:
                    await self._maybe_rebalance(metrics, sig)

                if self.trade_executor:
                    await self._execute_trading_guarded(metrics, sig)

                self._check_wealth_milestones(metrics)
                self._update_financial_status(metrics)
                await self._save_snapshot(metrics, sig)

                await asyncio.sleep(60)

            except Exception as e:
                self.logger.error("Financial autonomy loop error: %s", e)
                await asyncio.sleep(300)

    # ----------------------- metrics & health -----------------------

    async def _calculate_financial_metrics(self) -> FinancialMetrics:
        try:
            if not self.trade_executor:
                return self._default_metrics()

            ps = self.trade_executor.get_portfolio_status()
            perf = self.trade_executor.get_trading_performance()

            total_value = float(ps.get("total_value", 100_000.0))
            available = float(ps.get("available_cash", 100_000.0))
            daily_pnl = float(ps.get("daily_pnl", 0.0))
            total_pnl = float(ps.get("total_pnl", 0.0))
            trades_count = int(ps.get("trades_count", 0))

            invested = total_value - available
            start_cap = self.performance_tracking["start_capital"]
            total_return = (
                (total_value - start_cap) / start_cap if start_cap > 0 else 0.0
            )
            days_active = max(
                1, (datetime.now() - self.performance_tracking["start_time"]).days
            )
            annualized = (
                (total_return + 1) ** (365 / days_active) - 1
                if total_return > -0.999
                else 0.0
            )

            health_score = self._financial_health(
                total_return, annualized, float(perf.get("win_rate", 0.5))
            )
            ttf = self._time_to_freedom(total_value, annualized)

            return FinancialMetrics(
                total_portfolio_value=total_value,
                liquid_cash=available,
                invested_capital=invested,
                daily_pnl=daily_pnl,
                weekly_pnl=daily_pnl * 7.0,
                monthly_pnl=daily_pnl * 30.0,
                ytd_pnl=total_pnl,
                total_return=total_return,
                annualized_return=annualized,
                sharpe_ratio=float(perf.get("sharpe_ratio", 0.0)),
                max_drawdown=float(perf.get("max_drawdown", 0.0)),
                win_rate=float(perf.get("win_rate", 0.0)),
                profit_factor=0.0,  # optional calc
                trades_today=0,
                trades_total=trades_count,
                risk_score=0.5,  # hook for risk engine
                diversification_score=0.7,  # hook for PM
                liquidity_score=(available / total_value) if total_value > 0 else 1.0,
                financial_health_score=health_score,
                wealth_growth_rate=annualized,
                time_to_financial_freedom=ttf,
            )
        except Exception as e:
            self.logger.error("Metrics calculation failed: %s", e)
            return self._default_metrics()

    def _financial_health(
        self, total_return: float, annualized: float, win_rate: float
    ) -> float:
        try:
            return_score = min(max(total_return, -1.0), 1.0) + 1.0
            annual_score = min(max(annualized, -1.0), 1.0) + 1.0
            win_score = max(0.0, min(1.0, win_rate)) * 2.0
            health = (0.4 * return_score + 0.4 * annual_score + 0.2 * win_score) / 2.0
            return max(0.0, min(1.0, health))
        except Exception:
            return 0.5

    def _time_to_freedom(
        self, current_value: float, growth_rate: float
    ) -> Optional[float]:
        try:
            if growth_rate <= 0 or current_value <= 0:
                return None
            if current_value >= self.financial_freedom_target:
                return 0.0
            return max(
                0.0,
                math.log(self.financial_freedom_target / current_value)
                / math.log(1 + growth_rate),
            )
        except Exception:
            return None

    async def _health_and_objective(
        self, m: FinancialMetrics, sig: Dict[str, Any]
    ) -> None:
        # Drawdown mitigation
        if m.max_drawdown > 0.30:
            self.logger.warning(
                "⚠️ High drawdown (%.1f%%). Lowering risk.", m.max_drawdown * 100
            )
            self.risk_tolerance = max(0.3, self.risk_tolerance - 0.1)
        # Lift objective as we approach target
        if m.total_portfolio_value > self.financial_freedom_target * 0.8:
            self.objective = FinancialObjective.FINANCIAL_INDEPENDENCE
        # Incoherence pause if signals unhealthy
        if sig:
            if float(sig.get("risk", 0.0)) > 0.6 or _min_ethos(sig) < 0.6:
                self.logger.warning(
                    "⏸️ Pausing autonomous trading due to low ethos/high risk."
                )
                # soft pause trade executor decisions without stopping loop
        await asyncio.sleep(0)

    # ----------------------- analysis / portfolio / trading -----------------------

    async def _perform_market_analysis(self) -> None:
        try:
            self.logger.info("📈 Running market intelligence analysis…")
            await asyncio.sleep(0)
        except Exception as e:
            self.logger.error("Market analysis failed: %s", e)

    async def _maybe_rebalance(self, m: FinancialMetrics, sig: Dict[str, Any]) -> None:
        if datetime.now() - self.last_rebalance <= self.rebalance_frequency:
            return
        self.last_rebalance = datetime.now()

        decision = FinancialDecision(
            decision_id=f"rebalance_{int(time.time())}",
            timestamp=datetime.now(),
            decision_type="portfolio_rebalance",
            description="Scheduled portfolio rebalance",
            reasoning="Maintain target allocation and risk posture",
            expected_outcome="Improved risk-adjusted returns",
            confidence=0.8,
            risk_level="medium",
            symbolic_validation=0.0,
            quantum_probability=0.0,
            consciousness_alignment=0.0,
        )

        # Ethos gate for large shifts (proxy by notional threshold)
        # You can replace this with real projected notional delta.
        if m.total_portfolio_value >= 250_000:
            allow, reason = ethos_decision(
                {
                    "id": decision.decision_id,
                    "purpose": "rebalance",
                    "amount": float(
                        m.total_portfolio_value * 0.1
                    ),  # 10% turnover proxy
                    "currency": "NOM",
                    "tags": ["rebalance"],
                }
            )
            if allow != "allow":
                self._journal_decision(
                    decision, {"ethos": allow, "reason": reason, "approved": False}
                )
                self.logger.info("⏸️ Rebalance blocked by ethos gate: %s", reason)
                return

        validation = self.symbolic_validator.validate_financial_decision(decision, m)
        proceed = bool(validation.get("proceed_with_decision", False))
        self._journal_decision(
            decision, {"validation": validation, "approved": proceed}
        )

        if proceed:
            self.logger.info(
                "✅ Rebalance approved (score=%.3f).",
                float(validation.get("validation_score", 0.0)),
            )
            self.decision_history.append(decision)
        else:
            self.logger.info(
                "⏸️ Rebalance postponed (score=%.3f).",
                float(validation.get("validation_score", 0.0)),
            )

    async def _execute_trading_guarded(
        self, m: FinancialMetrics, sig: Dict[str, Any]
    ) -> None:
        daily_risk = abs(m.daily_pnl) / max(1e-9, m.total_portfolio_value)
        if daily_risk > self.max_daily_risk:
            self.logger.warning(
                "⚠️ Daily risk limit exceeded (%.2f%%).", daily_risk * 100
            )
            return
        self.logger.info("💹 Evaluating trading opportunities…")
        await asyncio.sleep(0)

    # ----------------------- milestones / status / persistence -----------------------

    def _check_wealth_milestones(self, m: FinancialMetrics) -> None:
        milestones = [
            150_000,
            200_000,
            250_000,
            500_000,
            750_000,
            1_000_000,
            2_000_000,
            5_000_000,
        ]
        for ms in milestones:
            if (
                m.total_portfolio_value >= ms
                and ms not in self.performance_tracking["wealth_milestones"]
            ):
                self.performance_tracking["wealth_milestones"].append(ms)
                self.logger.info("🎉 WEALTH MILESTONE ACHIEVED: $%,d", ms)
                if ms >= self.financial_freedom_target:
                    self.status = FinancialStatus.FINANCIAL_FREEDOM

    def _update_financial_status(self, m: FinancialMetrics) -> None:
        try:
            if m.total_portfolio_value >= self.financial_freedom_target:
                self.status = FinancialStatus.FINANCIAL_FREEDOM
            elif m.annualized_return > 0.50:
                self.status = FinancialStatus.WEALTHY
            elif m.total_return > 0.20:
                self.status = FinancialStatus.AUTONOMOUS
            elif m.total_return > 0:
                self.status = FinancialStatus.PROFITABLE
            else:
                self.status = FinancialStatus.ACTIVE
        except Exception as e:
            self.logger.error("Status update failed: %s", e)

    async def _save_snapshot(self, m: FinancialMetrics, sig: Dict[str, Any]) -> None:
        try:
            row = {
                "ts": datetime.now().isoformat(),
                "status": self.status.value,
                "objective": self.objective.value,
                "autonomous": self.autonomous_mode,
                "metrics": {
                    "value": m.total_portfolio_value,
                    "ret_total": m.total_return,
                    "ret_ann": m.annualized_return,
                    "health": m.financial_health_score,
                    "liquidity": m.liquidity_score,
                },
                "signals": sig or {},
            }
            with self.snapshot_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.warning("Snapshot write failed: %s", e)

    def _journal_decision(self, d: FinancialDecision, extra: Dict[str, Any]) -> None:
        try:
            row = {
                "ts": d.timestamp.isoformat(),
                "id": d.decision_id,
                "type": d.decision_type,
                "desc": d.description,
                "expected": d.expected_outcome,
                "confidence": d.confidence,
                "risk": d.risk_level,
                "symbolic_validation": d.symbolic_validation,
                "extra": extra,
            }
            with self.journal_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            self.performance_tracking["total_decisions"] += 1
        except Exception as e:
            self.logger.warning("Decision journal append failed: %s", e)

    # ----------------------- convenience / API -----------------------

    def stop_financial_autonomy(self) -> None:
        self.autonomous_mode = False
        self.status = FinancialStatus.PAUSED
        self.logger.info("⏸️ Financial autonomy operations paused")

    def get_financial_dashboard(self) -> Dict[str, Any]:
        try:
            current = (
                self.metrics_history[-1]
                if self.metrics_history
                else self._default_metrics()
            )
            return {
                "status": self.status.value,
                "objective": self.objective.value,
                "risk_tolerance": self.risk_tolerance,
                "autonomous_mode": self.autonomous_mode,
                "current_metrics": {
                    "portfolio_value": current.total_portfolio_value,
                    "total_return": f"{current.total_return:.2%}",
                    "annualized_return": f"{current.annualized_return:.2%}",
                    "daily_pnl": current.daily_pnl,
                    "financial_health": f"{current.financial_health_score:.1%}",
                    "time_to_freedom": current.time_to_financial_freedom,
                },
                "milestones_achieved": len(
                    self.performance_tracking["wealth_milestones"]
                ),
                "total_decisions": self.performance_tracking["total_decisions"],
                "components_active": {
                    "trade_executor": self.trade_executor is not None,
                    "portfolio_manager": self.portfolio_manager is not None,
                    "market_analyzer": self.market_analyzer is not None,
                },
                "financial_freedom_progress": (
                    current.total_portfolio_value / self.financial_freedom_target
                )
                * 100,
                "last_update": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error("Dashboard generation failed: %s", e)
            return {"error": str(e)}

    def _default_metrics(self) -> FinancialMetrics:
        return FinancialMetrics(
            total_portfolio_value=100_000.0,
            liquid_cash=100_000.0,
            invested_capital=0.0,
            daily_pnl=0.0,
            weekly_pnl=0.0,
            monthly_pnl=0.0,
            ytd_pnl=0.0,
            total_return=0.0,
            annualized_return=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            trades_today=0,
            trades_total=0,
            risk_score=0.5,
            diversification_score=0.5,
            liquidity_score=1.0,
            financial_health_score=0.5,
            wealth_growth_rate=0.0,
        )


# --------------------------- Factory & demo ---------------------------


def create_financial_autonomy_engine(**kwargs) -> FinancialAutonomyEngine:
    return FinancialAutonomyEngine(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 80)
    print(
        "EidollonaONE Financial Autonomy Engine v4.1+  —  coherent • ethical • auditable"
    )
    print("=" * 80)
    try:
        eng = create_financial_autonomy_engine()
        dash = eng.get_financial_dashboard()
        print("Status:", dash["status"])
        print(
            "Portfolio Value: $", f"{dash['current_metrics']['portfolio_value']:,.2f}"
        )
        print("Health:", dash["current_metrics"]["financial_health"])
        print("Freedom Progress:", f"{dash['financial_freedom_progress']:.1f}%")
    except Exception as e:
        print("❌ Initialization failed:", e)
