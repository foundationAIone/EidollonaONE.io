"""EidollonaONE Autonomous Portfolio Manager — SE41 v4.1+ aligned implementation."""

# trading_engine/autonomous_portfolio_manager.py
# ============================================================
# EidollonaONE Autonomous Portfolio Manager — SE41 v4.1+ aligned
# Consumes SymbolicEquation41 via a shared helper to:
#  - read SE41Signals safely (se41_signals())
#  - compute symbolic scoring for allocation (compute_symbolic_score)
#  - gate rebalancing ethically (ethos_decision)
# ============================================================

from __future__ import annotations

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
from typing import Dict, List, Optional, Any

# v4.1 core + shared context
from symbolic_core.symbolic_equation41 import SymbolicEquation41
from symbolic_core.se41_context import assemble_se41_context

# Shared trading helper (centralized; no in-file helper injection)
from trading.helpers.se41_trading_gate import se41_signals, ethos_decision

# Optional: link to the trade executor for actual orders (if present)
try:
    from trading_engine.ai_trade_executor import (
        AITradeExecutor,
        Portfolio,
    )

    TRADE_EXECUTOR_AVAILABLE = True
except Exception:
    TRADE_EXECUTOR_AVAILABLE = False

    class Portfolio:  # minimal fallback
        def __init__(self, **kwargs):
            self.total_value = 100_000.0
            self.available_cash = 100_000.0


# -------------------- Enums & dataclasses --------------------


class AssetClass(Enum):
    STOCKS = "stocks"
    BONDS = "bonds"
    CRYPTO = "crypto"
    COMMODITIES = "commodities"
    FOREX = "forex"
    REAL_ESTATE = "real_estate"
    CASH = "cash"
    DERIVATIVES = "derivatives"


class AllocationStrategy(Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    GROWTH = "growth"
    VALUE = "value"
    QUANTUM_OPTIMIZED = "quantum_optimized"
    CONSCIOUSNESS_GUIDED = "consciousness_guided"


@dataclass
class AssetAllocation:
    asset_class: AssetClass
    target_percentage: float
    min_percentage: float
    max_percentage: float
    current_percentage: float = 0.0
    current_value: float = 0.0
    rebalance_threshold: float = 0.05  # 5% deviation


@dataclass
class PortfolioOptimization:
    optimization_id: str
    strategy: AllocationStrategy
    target_allocations: Dict[AssetClass, float]
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    symbolic_coherence: float
    quantum_probability: float
    consciousness_alignment: float
    optimization_time: datetime = field(default_factory=datetime.now)


@dataclass
class RiskMetrics:
    var_95: float
    var_99: float
    cvar_95: float
    max_drawdown: float
    volatility: float
    beta: float
    correlation_risk: float
    concentration_risk: float
    liquidity_risk: float
    symbolic_risk_factor: float = 0.0


# -------------------- v4.1 helpers --------------------


def _min_ethos(s: Dict[str, Any]) -> float:
    e = s.get("ethos", {})
    return (
        min(
            e.get("authenticity", 0.0),
            e.get("integrity", 0.0),
            e.get("responsibility", 0.0),
            e.get("enrichment", 0.0),
        )
        if e
        else 0.0
    )


def compute_symbolic_score(s: Dict[str, Any]) -> float:
    """
    Convert SE41Signals into a scalar [0..1] for allocation logic.
    Weighted blend of coherence, mirror consistency, impetus (if present),
    and minimum ethos; then bounded.
    """
    if not s:
        return 0.0
    coh = float(s.get("coherence", 0.0))
    mc = float(s.get("mirror_consistency", 0.0))
    imp = float(s.get("impetus", 0.0)) if "impetus" in s else 0.7
    me = _min_ethos(s)
    raw = 0.45 * coh + 0.30 * mc + 0.15 * imp + 0.10 * me
    return max(0.0, min(1.0, raw))


# -------------------- Symbolic Optimizer --------------------


class SymbolicPortfolioOptimizer:
    """Symbolic equation-based allocation using SE41 signals."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.SymbolicPortfolioOptimizer")
        self._se41 = SymbolicEquation41()

    def optimize_portfolio_allocation(
        self,
        portfolio_value: float,
        strategy: AllocationStrategy,
        risk_tolerance: float,
        current_allocations: Dict[AssetClass, float],
    ) -> PortfolioOptimization:
        """
        Produce target allocations using SE41 signals, modulation by risk,
        and normalized diversification.
        """
        try:
            s = se41_signals()
            if not s:  # fallback to local evaluate if helper unavailable
                s = getattr(
                    self._se41.evaluate(assemble_se41_context()), "__dict__", {}
                )

            score = compute_symbolic_score(s)
            risk = float(s.get("risk", 0.2))
            unc = float(s.get("uncertainty", 0.2))

            # Modulate with risk/uncertainty (more risk/unc -> lower effective score)
            damp = max(0.4, 1.0 - 0.5 * (risk + unc))
            coherence = max(0.0, min(1.0, score * damp))

            target_alloc = self._generate_allocations(
                strategy, coherence, risk_tolerance
            )
            exp_ret = self._expected_return(target_alloc, coherence)
            exp_risk = self._expected_risk(target_alloc, risk_tolerance)
            sharpe = (exp_ret / exp_risk) if exp_risk > 1e-9 else 0.0

            opt = PortfolioOptimization(
                optimization_id=f"opt_{int(time.time())}_{uuid.uuid4().hex[:8]}",
                strategy=strategy,
                target_allocations=target_alloc,
                expected_return=exp_ret,
                expected_risk=exp_risk,
                sharpe_ratio=sharpe,
                symbolic_coherence=coherence,
                quantum_probability=0.0,  # can be set by an external quantum enhancer
                consciousness_alignment=0.0,  # can be set by a consciousness module
            )
            self.logger.info(
                "SE41 allocation: coherence=%.3f sharpe=%.3f", coherence, sharpe
            )
            return opt
        except Exception as e:
            self.logger.error("Portfolio optimization failed: %s", e)
            return self._fallback(strategy, risk_tolerance)

    # ---- internal calculation helpers ----

    def _base_allocations(
        self, strategy: AllocationStrategy
    ) -> Dict[AssetClass, float]:
        tables = {
            AllocationStrategy.CONSERVATIVE: {
                AssetClass.BONDS: 0.50,
                AssetClass.STOCKS: 0.30,
                AssetClass.CASH: 0.15,
                AssetClass.COMMODITIES: 0.05,
            },
            AllocationStrategy.MODERATE: {
                AssetClass.STOCKS: 0.50,
                AssetClass.BONDS: 0.30,
                AssetClass.CRYPTO: 0.10,
                AssetClass.COMMODITIES: 0.10,
            },
            AllocationStrategy.AGGRESSIVE: {
                AssetClass.STOCKS: 0.60,
                AssetClass.CRYPTO: 0.25,
                AssetClass.DERIVATIVES: 0.10,
                AssetClass.COMMODITIES: 0.05,
            },
            AllocationStrategy.GROWTH: {
                AssetClass.STOCKS: 0.70,
                AssetClass.CRYPTO: 0.20,
                AssetClass.BONDS: 0.10,
            },
            AllocationStrategy.VALUE: {
                AssetClass.STOCKS: 0.55,
                AssetClass.BONDS: 0.25,
                AssetClass.COMMODITIES: 0.15,
                AssetClass.CASH: 0.05,
            },
            AllocationStrategy.QUANTUM_OPTIMIZED: {
                AssetClass.CRYPTO: 0.40,
                AssetClass.STOCKS: 0.35,
                AssetClass.DERIVATIVES: 0.15,
                AssetClass.COMMODITIES: 0.10,
            },
            AllocationStrategy.CONSCIOUSNESS_GUIDED: {
                AssetClass.STOCKS: 0.45,
                AssetClass.CRYPTO: 0.30,
                AssetClass.BONDS: 0.15,
                AssetClass.COMMODITIES: 0.10,
            },
        }
        return tables.get(strategy, tables[AllocationStrategy.MODERATE])

    def _generate_allocations(
        self, strategy: AllocationStrategy, coherence: float, risk_tolerance: float
    ) -> Dict[AssetClass, float]:
        base = self._base_allocations(strategy)
        # symbolic & risk modulations
        coh_adj = (coherence - 0.5) * 0.2  # ±10%
        risk_adj = (1.0 - risk_tolerance) * 0.1

        adj: Dict[AssetClass, float] = {}
        total = 0.0
        for ac, w in base.items():
            if ac in (AssetClass.STOCKS, AssetClass.CRYPTO):
                delta = coh_adj
            elif ac in (AssetClass.BONDS, AssetClass.CASH):
                delta = risk_adj
            else:
                delta = coh_adj * 0.5
            x = max(0.01, w + delta)
            adj[ac] = x
            total += x

        # normalize to 100%
        if total > 0:
            for ac in adj:
                adj[ac] /= total
        return adj

    def _expected_return(
        self, alloc: Dict[AssetClass, float], coherence: float
    ) -> float:
        er = {
            AssetClass.STOCKS: 0.10,
            AssetClass.BONDS: 0.04,
            AssetClass.CRYPTO: 0.25,
            AssetClass.COMMODITIES: 0.08,
            AssetClass.FOREX: 0.06,
            AssetClass.REAL_ESTATE: 0.09,
            AssetClass.CASH: 0.02,
            AssetClass.DERIVATIVES: 0.15,
        }
        port = sum(alloc.get(ac, 0.0) * er.get(ac, 0.05) for ac in AssetClass)
        boost = (coherence - 0.5) * 0.05  # ±2.5%
        return max(0.01, port + boost)

    def _expected_risk(self, alloc: Dict[AssetClass, float], risk_tol: float) -> float:
        vol = {
            AssetClass.STOCKS: 0.18,
            AssetClass.BONDS: 0.06,
            AssetClass.CRYPTO: 0.60,
            AssetClass.COMMODITIES: 0.25,
            AssetClass.FOREX: 0.12,
            AssetClass.REAL_ESTATE: 0.15,
            AssetClass.CASH: 0.01,
            AssetClass.DERIVATIVES: 0.40,
        }
        var = sum((alloc.get(ac, 0.0) * vol.get(ac, 0.15)) ** 2 for ac in AssetClass)
        v = math.sqrt(var)
        # adjust by tolerance (higher tolerance → accept more risk)
        return max(0.05, v * (1.0 + (risk_tol - 0.5) * 0.2))

    def _fallback(
        self, strategy: AllocationStrategy, risk_tolerance: float
    ) -> PortfolioOptimization:
        base = self._base_allocations(strategy)
        exp_ret = self._expected_return(base, 0.65)
        exp_risk = self._expected_risk(base, risk_tolerance)
        return PortfolioOptimization(
            optimization_id=f"fallback_{int(time.time())}",
            strategy=strategy,
            target_allocations=base,
            expected_return=exp_ret,
            expected_risk=exp_risk,
            sharpe_ratio=(exp_ret / exp_risk) if exp_risk > 1e-9 else 0.0,
            symbolic_coherence=0.5,
            quantum_probability=0.5,
            consciousness_alignment=0.5,
        )


# -------------------- Quantum Risk (placeholder) --------------------


class QuantumRiskAssessment:
    """Quantum-enhanced portfolio risk assessment (simplified)."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.QuantumRiskAssessment")

    def assess_portfolio_risk(
        self,
        portfolio_value: float,
        allocations: Dict[AssetClass, float],
        historical_data: Optional[Dict[str, Any]] = None,
    ) -> RiskMetrics:
        try:
            volatility = self._portfolio_vol(allocations)
            var95 = self._var(portfolio_value, volatility, 0.95)
            var99 = self._var(portfolio_value, volatility, 0.99)
            cvar95 = var95 * 1.3
            concentration = self._concentration(allocations)
            correlation = self._correlation(allocations)
            liquidity = self._liquidity(allocations)

            # mild quantum adjustment
            q_unc = random.uniform(0.9, 1.1)
            return RiskMetrics(
                var_95=var95 * q_unc,
                var_99=var99 * q_unc,
                cvar_95=cvar95 * q_unc,
                max_drawdown=volatility * 2.5,
                volatility=volatility,
                beta=self._beta(allocations),
                correlation_risk=correlation,
                concentration_risk=concentration,
                liquidity_risk=liquidity,
                symbolic_risk_factor=0.0,
            )
        except Exception as e:
            self.logger.error("Risk assessment failed: %s", e)
            return RiskMetrics(
                var_95=portfolio_value * 0.05,
                var_99=portfolio_value * 0.08,
                cvar_95=portfolio_value * 0.07,
                max_drawdown=0.25,
                volatility=0.15,
                beta=1.0,
                correlation_risk=0.3,
                concentration_risk=0.4,
                liquidity_risk=0.2,
            )

    def _portfolio_vol(self, a: Dict[AssetClass, float]) -> float:
        vol = {
            AssetClass.STOCKS: 0.18,
            AssetClass.BONDS: 0.06,
            AssetClass.CRYPTO: 0.60,
            AssetClass.COMMODITIES: 0.25,
            AssetClass.FOREX: 0.12,
            AssetClass.REAL_ESTATE: 0.15,
            AssetClass.CASH: 0.01,
            AssetClass.DERIVATIVES: 0.40,
        }
        var = sum((a.get(ac, 0.0) * vol.get(ac, 0.15)) ** 2 for ac in AssetClass)
        return math.sqrt(var)

    def _var(self, pv: float, vol: float, conf: float) -> float:
        z = 1.645 if conf >= 0.95 and conf < 0.99 else 2.326
        daily = vol / math.sqrt(252.0)
        return pv * z * daily

    def _concentration(self, a: Dict[AssetClass, float]) -> float:
        if not a:
            return 0.4
        hhi = sum(x * x for x in a.values())
        n = max(1, len(a))
        min_hhi = 1.0 / n
        return max(0.0, min(1.0, (hhi - min_hhi) / (1.0 - min_hhi)))

    def _correlation(self, a: Dict[AssetClass, float]) -> float:
        pairs = [
            (AssetClass.STOCKS, AssetClass.DERIVATIVES),
            (AssetClass.CRYPTO, AssetClass.DERIVATIVES),
            (AssetClass.COMMODITIES, AssetClass.REAL_ESTATE),
        ]
        risk = 0.0
        for p, q in pairs:
            if p in a and q in a:
                risk += a[p] * a[q] * 0.8
        return min(1.0, risk)

    def _liquidity(self, a: Dict[AssetClass, float]) -> float:
        score = {
            AssetClass.CASH: 0.0,
            AssetClass.STOCKS: 0.1,
            AssetClass.BONDS: 0.2,
            AssetClass.FOREX: 0.1,
            AssetClass.CRYPTO: 0.3,
            AssetClass.COMMODITIES: 0.5,
            AssetClass.REAL_ESTATE: 0.8,
            AssetClass.DERIVATIVES: 0.4,
        }
        return sum(a.get(ac, 0.0) * score.get(ac, 0.5) for ac in AssetClass)

    def _beta(self, a: Dict[AssetClass, float]) -> float:
        beta = {
            AssetClass.STOCKS: 1.0,
            AssetClass.BONDS: 0.2,
            AssetClass.CRYPTO: 1.8,
            AssetClass.COMMODITIES: 0.8,
            AssetClass.FOREX: 0.3,
            AssetClass.REAL_ESTATE: 0.6,
            AssetClass.CASH: 0.0,
            AssetClass.DERIVATIVES: 1.5,
        }
        return sum(a.get(ac, 0.0) * beta.get(ac, 1.0) for ac in AssetClass)


# -------------------- Autonomous Portfolio Manager --------------------


class AutonomousPortfolioManager:
    """
    EidollonaONE Autonomous Portfolio Manager — SE41 v4.1+
    Symbolic optimization (SE41), quantum risk (optional), ethos-gated rebalancing.
    """

    def __init__(self, manager_directory: Optional[str] = None) -> None:
        self.logger = logging.getLogger(f"{__name__}.AutonomousPortfolioManager")

        self.manager_directory = Path(manager_directory or "portfolio_manager_data")
        self.manager_directory.mkdir(exist_ok=True)

        self.symbolic_optimizer = SymbolicPortfolioOptimizer()
        self.quantum_risk_assessor = QuantumRiskAssessment()

        self.current_strategy = AllocationStrategy.MODERATE
        self.risk_tolerance = 0.6  # 0..1
        self.target_allocations: Dict[AssetClass, AssetAllocation] = {}
        self.optimization_history: List[PortfolioOptimization] = []
        self.risk_metrics_history: List[RiskMetrics] = []

        self.executor_available = False
        self.trade_executor: Optional[AITradeExecutor] = None
        if TRADE_EXECUTOR_AVAILABLE:
            try:
                self.trade_executor = AITradeExecutor()
                self.executor_available = True
            except Exception as e:
                self.logger.warning("Trade executor not available: %s", e)

        self.auto_rebalance_enabled = True
        self.rebalance_threshold = 0.05
        self.last_optimization: Optional[PortfolioOptimization] = None
        self.last_risk_assessment: Optional[RiskMetrics] = None

        self.logger.info("EidollonaONE Autonomous Portfolio Manager v4.1+ initialized")
        self.logger.info(
            "Symbolic Optimization: ✅ | Quantum Risk: ✅ | Executor: %s",
            "✅" if self.executor_available else "❌",
        )

    # ---------- public API ----------

    def optimize(self, portfolio: Portfolio) -> PortfolioOptimization:
        """Run SE41 optimization and store result."""
        opt = self.symbolic_optimizer.optimize_portfolio_allocation(
            portfolio_value=portfolio.total_value,
            strategy=self.current_strategy,
            risk_tolerance=self.risk_tolerance,
            current_allocations=self._current_alloc_map(),
        )
        self.optimization_history.append(opt)
        self.last_optimization = opt
        self._update_targets_from(opt)
        return opt

    def assess_risk(self, portfolio: Portfolio) -> RiskMetrics:
        """Run quantum-enhanced risk metrics and store result."""
        alloc = {
            k: v.target_percentage for k, v in self.target_allocations.items()
        } or self._default_alloc()
        rm = self.quantum_risk_assessor.assess_portfolio_risk(
            portfolio.total_value, alloc
        )
        self.risk_metrics_history.append(rm)
        self.last_risk_assessment = rm
        return rm

    def maybe_rebalance(self, portfolio: Portfolio) -> List[Dict[str, Any]]:
        """
        If deviations exceed threshold, propose and (if executor exists) submit
        ethos-gated rebalancing orders. Returns list of proposed/placed actions.
        """
        actions: List[Dict[str, Any]] = []
        if not self.auto_rebalance_enabled:
            return actions
        if not self.target_allocations:
            return actions

        current_values = self._estimate_current_values(portfolio)
        total = sum(current_values.values()) or 1.0

        for ac, cfg in self.target_allocations.items():
            current_pct = current_values.get(ac, 0.0) / total
            dev = current_pct - cfg.target_percentage
            if abs(dev) < cfg.rebalance_threshold:
                continue

            # determine action size/value
            delta_value = (cfg.target_percentage - current_pct) * total
            side = "buy" if delta_value > 0 else "sell"
            notional = abs(delta_value)

            # ethos gate — mandatory
            tx = {
                "id": f"rebalance_{ac.value}_{int(time.time())}",
                "purpose": "portfolio_rebalance",
                "amount": float(notional),
                "currency": "USD",
                "tags": ["service", "rebalance"],
            }
            decision, reason = ethos_decision(tx)
            actions.append(
                {
                    "asset": ac.value,
                    "side": side,
                    "notional": notional,
                    "ethos_decision": decision,
                    "reason": reason,
                }
            )

            if decision != "allow":
                self.logger.warning(
                    "Rebalance blocked (%s): %s Δ=%.2f%%", reason, ac.value, dev * 100.0
                )
                continue

            # Place orders only if an executor is available (this demo skips real order wiring)
            if self.executor_available and self.trade_executor:
                self.logger.info(
                    "Rebalance approved: %s %s $%.2f", ac.value, side, notional
                )
                # You can route to AITradeExecutor here with a synth signal or an OTC order adapter.

        return actions

    # ---------- internal helpers ----------

    def _current_alloc_map(self) -> Dict[AssetClass, float]:
        return {
            ac: cfg.current_percentage for ac, cfg in self.target_allocations.items()
        }

    def _update_targets_from(self, opt: PortfolioOptimization) -> None:
        self.target_allocations = {
            ac: AssetAllocation(
                asset_class=ac,
                target_percentage=pct,
                min_percentage=max(0.0, pct - 0.05),
                max_percentage=min(1.0, pct + 0.05),
                rebalance_threshold=self.rebalance_threshold,
            )
            for ac, pct in opt.target_allocations.items()
        }

    def _estimate_current_values(self, portfolio: Portfolio) -> Dict[AssetClass, float]:
        """
        A placeholder estimator: split current portfolio value proportional
        to target allocations unless live position data is available.
        """
        if not self.target_allocations:
            return self._default_values(portfolio.total_value)
        return {
            ac: cfg.target_percentage * portfolio.total_value
            for ac, cfg in self.target_allocations.items()
        }

    def _default_alloc(self) -> Dict[AssetClass, float]:
        return {
            AssetClass.STOCKS: 0.5,
            AssetClass.BONDS: 0.3,
            AssetClass.CRYPTO: 0.1,
            AssetClass.COMMODITIES: 0.1,
        }

    def _default_values(self, total: float) -> Dict[AssetClass, float]:
        alloc = self._default_alloc()
        return {ac: pct * total for ac, pct in alloc.items()}


# -------------------- Factory & CLI --------------------


def create_portfolio_manager(**kwargs) -> AutonomousPortfolioManager:
    return AutonomousPortfolioManager(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 70)
    print("EidollonaONE Autonomous Portfolio Manager v4.1+")
    print("Framework: Symbolic Equation v4.1+ with Ethos-Gated Allocation")
    print("Purpose: Optimal Portfolio Management and Risk Control")
    print("=" * 70)

    try:
        print("\n🏦 Initializing Autonomous Portfolio Manager...")
        mgr = create_portfolio_manager()
        print("✅ Portfolio Manager initialized successfully!")
        print("🚀 Ready for autonomous portfolio optimization!")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
