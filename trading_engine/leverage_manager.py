# trading_engine/leverage_manager.py
# ===================================================================
# EidollonaONE Leverage Manager — SE41 v4.1+ aligned
#
# What’s new
# - Ingests SE41Signals each optimization (se41_signals()).
# - Bounded target leverage: +coherence/+ethos, −risk/−uncertainty/−volatility.
# - Ethos-gates leverage increases (ethos_decision) before apply.
# - Safety rails: equity ratio / margin utilization / VaR / correlation limits.
# - Journal JSONL for every recommendation and apply/deny outcome.
# ===================================================================

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import deque

from symbolic_core.symbolic_equation41 import SymbolicEquation41
from trading.helpers.se41_trading_gate import se41_signals, ethos_decision, se41_numeric

# Optional cross-module imports (guarded)
try:
    from trading_engine.position_manager import Position, PositionType  # noqa: F401
    from trading_engine.risk_management import RiskAssessment  # noqa: F401

    TRADE_COMPONENTS_AVAILABLE = True
except Exception:
    TRADE_COMPONENTS_AVAILABLE = False


# --------------------------- enums & models ---------------------------


class LeverageLevel(Enum):
    CONSERVATIVE = "conservative"  # 1:1 .. 1:2
    MODERATE = "moderate"  # 1:2 .. 1:5
    AGGRESSIVE = "aggressive"  # 1:5 .. 1:10
    HIGH_RISK = "high_risk"  # 1:10 .. 1:20
    EXTREME = "extreme"  # 1:20+
    ADAPTIVE = "adaptive"


class LeverageStrategy(Enum):
    FIXED = "fixed"
    VOLATILITY_BASED = "volatility_based"
    MOMENTUM_BASED = "momentum_based"
    RISK_PARITY = "risk_parity"
    KELLY_CRITERION = "kelly_criterion"
    SYMBOLIC_ADAPTIVE = "symbolic_adaptive"
    QUANTUM_OPTIMAL = "quantum_optimal"


class MarginStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    MARGIN_CALL = "margin_call"
    LIQUIDATION = "liquidation"


class LeverageRisk(Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"
    CATASTROPHIC = "catastrophic"


@dataclass
class LeverageConfig:
    strategy: LeverageStrategy = LeverageStrategy.SYMBOLIC_ADAPTIVE
    max_leverage: float = 10.0
    min_leverage: float = 1.0
    target_leverage: float = 3.0

    # Portfolio risk rails
    max_portfolio_risk: float = 0.05  # 5% (per engine’s definition)
    volatility_threshold: float = 0.30
    correlation_limit: float = 0.70

    # Dynamics
    leverage_adjustment_speed: float = 0.10  # fraction toward target per apply()
    rebalance_threshold: float = 0.20  # 20% relative diff triggers apply

    # Margin rails
    margin_requirement: float = 0.25
    margin_call_threshold: float = 0.30
    liquidation_threshold: float = 0.20

    # SE41 floors
    symbolic_coherence_min: float = 0.50
    quantum_stability_min: float = 0.60


@dataclass
class LeveragePosition:
    symbol: str
    position_size: float
    notional_value: float
    leverage_ratio: float
    margin_used: float
    margin_requirement: float
    var_contribution: float = 0.0
    correlation_risk: float = 0.0
    liquidity_risk: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    symbolic_coherence: float = 0.0
    quantum_stability: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class PortfolioLeverage:
    total_equity: float = 0.0
    total_margin_used: float = 0.0
    available_margin: float = 0.0
    gross_leverage: float = 1.0
    net_leverage: float = 1.0

    portfolio_var: float = 0.0
    margin_utilization: float = 0.0
    equity_ratio: float = 1.0

    margin_status: MarginStatus = MarginStatus.HEALTHY
    leverage_risk: LeverageRisk = LeverageRisk.LOW

    max_leverage_allowed: float = 10.0
    current_leverage_target: float = 3.0

    portfolio_coherence: float = 0.0
    quantum_leverage_stability: float = 0.0


@dataclass
class LeverageRecommendation:
    recommendation_id: str
    action: str  # increase | decrease | maintain | rebalance
    target_leverage: float
    current_leverage: float
    confidence: float = 0.0
    reason: str = ""
    risk_impact: str = "neutral"
    expected_return_impact: float = 0.0
    urgency: str = "normal"  # low | normal | high | critical
    implementation_steps: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    symbolic_strength: float = 0.0
    quantum_probability: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


# --------------------------- v4.1 helpers ---------------------------


def _ethos_min(sig: Dict[str, Any]) -> float:
    e = sig.get("ethos", {}) if isinstance(sig, dict) else {}
    if not e:
        return 0.0
    return min(
        float(e.get("authenticity", 0.0)),
        float(e.get("integrity", 0.0)),
        float(e.get("responsibility", 0.0)),
        float(e.get("enrichment", 0.0)),
    )


def _bounded_target_from_se41(
    se: Dict[str, Any], vol: float, corr: float, var: float, cfg: LeverageConfig
) -> float:
    """
    Compute a bounded leverage target (>=1.0) from SE41 + risk.
    Reward: coherence, ethos, opportunity (mirror_consistency optional)
    Damp: risk, uncertainty, realized volatility, correlation, VaR
    """
    if not se:
        # Conservative baseline if no signals
        base = max(cfg.min_leverage, min(cfg.target_leverage, cfg.max_leverage))
        base *= 1.0 - 0.25 * min(vol, 1.0) - 0.25 * min(corr, 1.0)
        return max(cfg.min_leverage, min(base, cfg.max_leverage))

    coh = float(se.get("coherence", 0.5))
    mc = float(se.get("mirror_consistency", 0.5))
    ethos = _ethos_min(se)
    risk = float(se.get("risk", 0.25))
    unc = float(se.get("uncertainty", 0.25))

    # Reward: coherence / ethos / consistency
    up = 1.0 + 0.60 * coh + 0.25 * ethos + 0.15 * mc
    # Damp: risk / uncertainty / realized vol / correlation / VaR
    down = (
        1.0
        + 0.90 * risk
        + 0.60 * unc
        + 0.50 * min(vol, 1.0)
        + 0.35 * min(corr, 1.0)
        + 0.40 * min(var / 0.05, 1.0)
    )

    raw = cfg.target_leverage * up / max(down, 1e-6)
    # Respect coherence floor
    raw *= max(cfg.symbolic_coherence_min, coh)
    # Enforce global bounds
    return max(cfg.min_leverage, min(raw, cfg.max_leverage))


# --------------------------- optimizers & controllers ---------------------------


class SymbolicLeverageOptimizer:
    """SE41-driven leverage optimizer with numeric pulse for entropy."""

    def __init__(self, config: LeverageConfig):
        self.logger = logging.getLogger(f"{__name__}.SymbolicLeverageOptimizer")
        self.config = config
        self._se41 = SymbolicEquation41()

    def optimize(
        self,
        portfolio_data: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            # Pull SE41 snapshot
            se = se41_signals() or {}
            vol = float(market.get("volatility", 0.2))
            corr = float(risk.get("correlation_risk", 0.3))
            var = float(risk.get("portfolio_var", 0.01))

            # Optional numeric pulse (harmless; helps stochasticity)
            try:
                _ = se41_numeric(
                    M_t=se.get("coherence", 0.5),
                    DNA_states=[1.0, vol, corr, var, 1.1],
                    harmonic_patterns=[1.0, 1.1, vol, corr, var, 1.2],
                )
            except Exception:
                pass

            current_lev = float(portfolio_data.get("gross_leverage", 1.0))
            target = _bounded_target_from_se41(se, vol, corr, var, self.config)

            # Recommendation framing
            rel = abs(target - current_lev) / max(current_lev, 1e-9)
            if rel < 0.10:
                action = "maintain"
            else:
                action = "increase" if target > current_lev else "decrease"

            # Confidence increases with coherence and ethos, decreases with risk
            conf = max(
                0.0,
                min(
                    1.0,
                    0.45 * float(se.get("coherence", 0.5))
                    + 0.25 * _ethos_min(se)
                    - 0.20 * float(se.get("risk", 0.25))
                    - 0.10 * float(se.get("uncertainty", 0.25)),
                ),
            )

            rec = LeverageRecommendation(
                recommendation_id=f"levrec_{int(time.time())}",
                action=action,
                target_leverage=target,
                current_leverage=current_lev,
                confidence=conf,
                reason="SE41-bounded leverage target",
                risk_impact=(
                    "negative"
                    if action == "increase"
                    and (
                        var > self.config.max_portfolio_risk
                        or corr > self.config.correlation_limit
                    )
                    else "neutral"
                ),
                expected_return_impact=0.0,
                urgency=("high" if rel >= 0.3 else "normal"),
                implementation_steps=(
                    ["gradual_scale", "monitor_var_correlation", "margin_buffer"]
                ),
            )
            return {
                "valid": True,
                "signals": se,
                "recommendation": rec,
                "coherence": float(se.get("coherence", 0.5)),
                "risk": float(se.get("risk", 0.25)),
                "uncertainty": float(se.get("uncertainty", 0.25)),
                "ts": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error("Leverage optimization failed: %s", e)
            return {"valid": False, "error": str(e)}


class QuantumLeverageController:
    """Quantum-enhanced risk lens for leverage posture."""

    def __init__(self, config: LeverageConfig):
        self.logger = logging.getLogger(f"{__name__}.QuantumLeverageController")
        self.config = config
        self.leverage_history = deque(maxlen=1000)

    def assess(
        self,
        pl: PortfolioLeverage,
        market_vol: float,
        positions: List[LeveragePosition],
    ) -> Dict[str, Any]:
        try:
            # Volatility & leverage amplify risk
            volatility_risk = min(market_vol * max(pl.gross_leverage, 1.0), 1.0)
            concentration_risk = self._concentration(positions)
            correlation_risk = self._correlation(positions)

            quantum_randomness = random.uniform(0.95, 1.05)
            base = (
                0.30 * volatility_risk
                + 0.25 * concentration_risk
                + 0.25 * correlation_risk
                + 0.20 * pl.margin_utilization
            )
            risk_score = min(
                1.0, base * (1.0 + (pl.gross_leverage - 1.0) * 0.1) * quantum_randomness
            )
            pl.quantum_leverage_stability = 1.0 - risk_score
            pl.leverage_risk = self._bucket(risk_score)
            pl.margin_status = self._margin(pl)

            return {
                "risk_score": risk_score,
                "volatility_risk": volatility_risk,
                "concentration_risk": concentration_risk,
                "correlation_risk": correlation_risk,
                "margin_status": pl.margin_status.value,
                "leverage_risk": pl.leverage_risk.value,
            }
        except Exception as e:
            self.logger.error("Leverage risk assessment failed: %s", e)
            return {
                "risk_score": 0.5,
                "margin_status": "warning",
                "leverage_risk": "moderate",
            }

    # --- internals

    def _concentration(self, positions: List[LeveragePosition]) -> float:
        if not positions:
            return 0.0
        total = sum(p.notional_value for p in positions) or 1.0
        weights = [(p.notional_value / total) for p in positions]
        hhi = sum(w * w for w in weights)
        return min(1.0, hhi * 2.0)

    def _correlation(self, positions: List[LeveragePosition]) -> float:
        if not positions:
            return 0.0
        return min(1.0, sum(p.correlation_risk for p in positions) / len(positions))

    def _bucket(self, score: float) -> LeverageRisk:
        if score < 0.2:
            return LeverageRisk.MINIMAL
        if score < 0.4:
            return LeverageRisk.LOW
        if score < 0.6:
            return LeverageRisk.MODERATE
        if score < 0.8:
            return LeverageRisk.HIGH
        if score < 0.95:
            return LeverageRisk.EXTREME
        return LeverageRisk.CATASTROPHIC

    def _margin(self, pl: PortfolioLeverage) -> MarginStatus:
        eq = pl.equity_ratio
        mu = pl.margin_utilization
        if eq <= 0.20:
            return MarginStatus.LIQUIDATION
        if eq <= 0.30:
            return MarginStatus.MARGIN_CALL
        if mu > 0.80 or eq < 0.40:
            return MarginStatus.CRITICAL
        if mu > 0.60 or eq < 0.60:
            return MarginStatus.WARNING
        return MarginStatus.HEALTHY


# --------------------------- manager (facade) ---------------------------


class LeverageManager:
    """
    Dynamic leverage manager that:
      - Optimizes target leverage with SE41
      - Checks quantum / margin / correlation rails
      - Ethos-gates leverage increases
      - Applies change gradually with adjustment speed
      - Journals outcome for audit
    """

    def __init__(
        self, config: Optional[LeverageConfig] = None, data_dir: Optional[str] = None
    ):
        self.logger = logging.getLogger(f"{__name__}.LeverageManager")
        self.config = config or LeverageConfig()
        self.optimizer = SymbolicLeverageOptimizer(self.config)
        self.controller = QuantumLeverageController(self.config)

        self.portfolio_leverage = PortfolioLeverage(
            max_leverage_allowed=self.config.max_leverage,
            current_leverage_target=self.config.target_leverage,
        )
        self.leverage_positions: Dict[str, LeveragePosition] = {}
        self.leverage_recommendations: List[LeverageRecommendation] = []

        self.leverage_history = deque(maxlen=1000)
        self.risk_history = deque(maxlen=1000)

        self._dir = Path(data_dir or "leverage_data")
        self._dir.mkdir(exist_ok=True)
        self._journal_path = self._dir / "leverage_journal.jsonl"

        self.last_optimization_time = datetime.now()
        self.optimization_interval = 60  # seconds

        self.logger.info(
            "Leverage Manager v4.1+ initialized; target=%sx, bounds=[%sx,%sx]",
            self.config.target_leverage,
            self.config.min_leverage,
            self.config.max_leverage,
        )

    # ---- public API

    def tick_optimize(
        self,
        portfolio_snapshot: Dict[str, Any],
        market_snapshot: Dict[str, Any],
        risk_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run one optimization pass. Returns dict with recommendation and (if applied) updated leverage.
        """
        # 1) Optimize with SE41
        opt = self.optimizer.optimize(
            portfolio_snapshot, market_snapshot, risk_snapshot
        )
        if not opt.get("valid", False):
            self._journal(
                {
                    "type": "optimize_error",
                    "error": opt.get("error", "unknown"),
                    "ts": datetime.now().isoformat(),
                }
            )
            return {"valid": False, "error": opt.get("error", "unknown")}

        rec: LeverageRecommendation = opt["recommendation"]

        # 2) Quantum / margin rails assessment
        pl = self._refresh_portfolio_leverage(portfolio_snapshot)
        rail = self.controller.assess(
            pl,
            market_snapshot.get("volatility", 0.2),
            list(self.leverage_positions.values()),
        )
        self.risk_history.append(rail)

        # Hard safety rails: deny increases if rails are red
        if rec.action == "increase":
            if (
                pl.margin_status
                in [
                    MarginStatus.CRITICAL,
                    MarginStatus.MARGIN_CALL,
                    MarginStatus.LIQUIDATION,
                ]
                or rail["risk_score"] >= 0.80
                or risk_snapshot.get("portfolio_var", 0.01)
                > self.config.max_portfolio_risk
                or risk_snapshot.get("correlation_risk", 0.3)
                > self.config.correlation_limit
            ):
                self._journal(
                    {
                        "type": "deny_increase_rails",
                        "rec": _rec_dict(rec),
                        "rail": rail,
                        "ts": datetime.now().isoformat(),
                    }
                )
                return {"valid": True, "applied": False, "reason": "safety_rails"}

        # 3) Ethos gate (only on increases)
        ethos_gate = "skip"
        if rec.action == "increase":
            amount = max(
                1.0,
                pl.total_equity
                * (rec.target_leverage - pl.gross_leverage)
                / max(rec.current_leverage, 1.0),
            )
            allow, reason = ethos_decision(
                {
                    "id": rec.recommendation_id,
                    "purpose": "leverage_increase",
                    "amount": float(amount),
                    "currency": "NOM",
                    "tags": ["leverage", "risk", "portfolio"],
                }
            )
            ethos_gate = allow
            if allow == "deny":
                self._journal(
                    {
                        "type": "ethos_deny",
                        "reason": reason,
                        "rec": _rec_dict(rec),
                        "ts": datetime.now().isoformat(),
                    }
                )
                return {
                    "valid": True,
                    "applied": False,
                    "reason": f"ethos_deny:{reason}",
                }

        # 4) Apply if meaningful change
        if rec.action in ("increase", "decrease"):
            applied = self._apply_leverage_target(pl, rec.target_leverage)
            self.leverage_recommendations.append(rec)
            self._journal(
                {
                    "type": "apply",
                    "rec": _rec_dict(rec),
                    "ethos": ethos_gate,
                    "after": _pl_dict(self.portfolio_leverage),
                    "ts": datetime.now().isoformat(),
                }
            )
            return {
                "valid": True,
                "applied": applied,
                "after": _pl_dict(self.portfolio_leverage),
            }

        # maintain or rebalance
        self._journal(
            {
                "type": "maintain",
                "rec": _rec_dict(rec),
                "ts": datetime.now().isoformat(),
            }
        )
        return {"valid": True, "applied": False, "reason": "maintain"}

    def status(self) -> Dict[str, Any]:
        se = se41_signals() or {}
        return {
            "portfolio": _pl_dict(self.portfolio_leverage),
            "ethos_min": _ethos_min(se),
            "se41": {
                "coherence": se.get("coherence", 0.0),
                "risk": se.get("risk", 0.0),
                "uncertainty": se.get("uncertainty", 0.0),
                "mirror_consistency": se.get("mirror_consistency", 0.0),
            },
            "ts": datetime.now().isoformat(),
        }

    # ---- internals

    def _apply_leverage_target(self, pl: PortfolioLeverage, target: float) -> bool:
        current = float(pl.gross_leverage)
        if current <= 0:
            pl.gross_leverage = max(
                self.config.min_leverage, min(target, self.config.max_leverage)
            )
            return True
        rel = abs(target - current) / current
        if rel < self.config.rebalance_threshold:
            return False
        # Move a fraction toward target
        step = self.config.leverage_adjustment_speed
        new_lev = current + step * (target - current)
        pl.gross_leverage = max(
            self.config.min_leverage, min(new_lev, self.config.max_leverage)
        )
        pl.current_leverage_target = target
        return True

    def _refresh_portfolio_leverage(self, snap: Dict[str, Any]) -> PortfolioLeverage:
        pl = self.portfolio_leverage
        pl.total_equity = float(snap.get("total_equity", pl.total_equity))
        pl.total_margin_used = float(
            snap.get("total_margin_used", pl.total_margin_used)
        )
        pl.available_margin = float(snap.get("available_margin", pl.available_margin))
        pl.gross_leverage = max(
            self.config.min_leverage,
            float(snap.get("gross_leverage", pl.gross_leverage)),
        )
        pl.net_leverage = max(
            self.config.min_leverage, float(snap.get("net_leverage", pl.net_leverage))
        )
        total_margin = max(pl.total_margin_used + pl.available_margin, 1e-9)
        pl.margin_utilization = min(1.0, pl.total_margin_used / total_margin)
        # Equity ratio proxy
        pl.equity_ratio = min(
            1.0,
            max(
                0.0, pl.total_equity / max(pl.total_equity + pl.total_margin_used, 1e-9)
            ),
        )
        return pl

    def _journal(self, obj: Dict[str, Any]) -> None:
        try:
            with self._journal_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(obj) + "\n")
        except Exception:
            pass


# --------------------------- factory ---------------------------


def create_leverage_manager(**kwargs) -> LeverageManager:
    return LeverageManager(**kwargs)


# --------------------------- demo ---------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 72)
    print("EidollonaONE Leverage Manager v4.1+ — coherent • ethical • risk-aware")
    print("=" * 72)

    mgr = create_leverage_manager()

    # Mock snapshots
    portfolio = {
        "total_equity": 250_000.0,
        "total_margin_used": 40_000.0,
        "available_margin": 60_000.0,
        "gross_leverage": 2.8,
        "net_leverage": 2.4,
    }
    market = {"volatility": 0.22}
    risk = {"portfolio_var": 0.018, "correlation_risk": 0.35}

    out = mgr.tick_optimize(portfolio, market, risk)
    print(json.dumps(out, indent=2))
    print(json.dumps(mgr.status(), indent=2))


# --------------------------- utils (private) ---------------------------


def _pl_dict(pl: PortfolioLeverage) -> Dict[str, Any]:
    return {
        "total_equity": pl.total_equity,
        "margin_used": pl.total_margin_used,
        "available_margin": pl.available_margin,
        "gross_leverage": pl.gross_leverage,
        "net_leverage": pl.net_leverage,
        "margin_utilization": pl.margin_utilization,
        "equity_ratio": pl.equity_ratio,
        "margin_status": pl.margin_status.value,
        "leverage_risk": pl.leverage_risk.value,
        "max_leverage_allowed": pl.max_leverage_allowed,
        "current_leverage_target": pl.current_leverage_target,
        "portfolio_coherence": pl.portfolio_coherence,
        "quantum_leverage_stability": pl.quantum_leverage_stability,
    }


def _rec_dict(rec: LeverageRecommendation) -> Dict[str, Any]:
    return {
        "id": rec.recommendation_id,
        "action": rec.action,
        "target": rec.target_leverage,
        "current": rec.current_leverage,
        "confidence": rec.confidence,
        "reason": rec.reason,
        "urgency": rec.urgency,
        "symbolic_strength": rec.symbolic_strength,
        "quantum_probability": rec.quantum_probability,
        "ts": rec.timestamp.isoformat(),
    }
