"""
Shim: position_manager consolidated into core trading engine.

Legacy imports used to point at TradingEngine, but projects still import
PositionManager directly. This module keeps those imports working and
exposes a SE41-aligned PositionManager that plugs into the current stack.
"""

from __future__ import annotations

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

# Legacy shim surface (kept for historical imports)
try:
    from trading_engine import TradingEngine, TradeSignal, ExecutionRecord  # noqa: F401

    __all__ = [
        "TradingEngine",
        "TradeSignal",
        "ExecutionRecord",
        "PositionManager",
        "Position",
        "PositionType",
        "PositionStatus",
        "PositionSummary",
    ]
except Exception:
    __all__ = [
        "PositionManager",
        "Position",
        "PositionType",
        "PositionStatus",
        "PositionSummary",
    ]

# ---- SE41 unified imports ---------------------------------------------------
from symbolic_core.symbolic_equation41 import SymbolicEquation41
from trading.helpers.se41_trading_gate import se41_numeric  # numeric synthesis

# ---- Adjacent dependencies (graceful fallbacks) ----------------------------
try:
    from trading_engine.ai_trade_executor import (
        TradeExecution,
    )

    TRADE_EXECUTOR_AVAILABLE = True
except Exception:
    TRADE_EXECUTOR_AVAILABLE = False

    class TradeExecution:  # minimal stand-in
        def __init__(
            self,
            symbol: str,
            trade_type: str,
            position_size: float,
            executed_price: float,
            fees: float = 0.0,
        ):
            self.symbol = symbol
            self.trade_type = trade_type
            self.position_size = float(position_size)
            self.executed_price = float(executed_price)
            self.fees = float(fees)


# --------------------------- position types & models -------------------------


class PositionType(Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class PositionStatus(Enum):
    ACTIVE = "active"
    CLOSING = "closing"
    CLOSED = "closed"
    SUSPENDED = "suspended"


@dataclass
class Position:
    """Enhanced position with symbolic validation & risk tracking."""

    position_id: str
    symbol: str
    position_type: PositionType
    quantity: float
    entry_price: float

    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: PositionStatus = PositionStatus.ACTIVE

    # Tracking
    entry_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    cost_basis: float = 0.0
    fees_paid: float = 0.0

    # SE41/quantum hooks
    symbolic_coherence: float = 0.0
    quantum_probability: float = 0.0
    consciousness_alignment: float = 0.0
    risk_score: float = 0.0

    # Diagnostics
    max_profit: float = 0.0
    max_loss: float = 0.0
    holding_period_hours: float = 0.0
    volatility_exposure: float = 0.0


@dataclass
class PositionSummary:
    total_positions: int = 0
    long_positions: int = 0
    short_positions: int = 0
    total_market_value: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    total_fees: float = 0.0
    average_symbolic_coherence: float = 0.0
    portfolio_risk_score: float = 0.0
    diversification_score: float = 0.0


# --------------------------- symbolic validator -----------------------------


class SymbolicPositionValidator:
    """SE41-bounded coherence validator for an individual position."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SymbolicPositionValidator")
        self._se41 = SymbolicEquation41()

    def validate_position_coherence(
        self, position: Position, portfolio_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Produces bounded numeric synthesis for a position using:
        size, pnl, time held, volatility exposure, portfolio risk/diversification/exposure.
        """
        try:
            size_factor = min(abs(position.quantity) / 10000.0, 1.0)
            # scale pnl to a small band (±1.0 over a $10k reference)
            pnl_factor = max(-1.0, min(position.unrealized_pnl / 10000.0, 1.0))
            time_factor = min(
                max(position.holding_period_hours, 0.0) / 168.0, 1.0
            )  # 1 week
            vol_factor = min(max(position.volatility_exposure, 0.0), 1.0)

            port_risk = float(portfolio_context.get("risk_level", 0.5))
            diversification = float(portfolio_context.get("diversification", 0.7))
            exposure = float(portfolio_context.get("total_exposure", 0.5))

            numeric = se41_numeric(
                M_t=max(0.0, 1.0 - port_risk),  # higher portfolio risk → lower M_t
                DNA_states=[
                    1.0,
                    size_factor,
                    pnl_factor,
                    time_factor,
                    vol_factor,
                    diversification,
                    exposure,
                    1.1,
                ],
                harmonic_patterns=[
                    1.0,
                    1.2,
                    size_factor,
                    pnl_factor,
                    time_factor,
                    vol_factor,
                    (1.0 - port_risk),
                    diversification,
                    exposure,
                    1.3,
                ],
            )

            ok = (
                isinstance(numeric, (int, float))
                and math.isfinite(numeric)
                and 0.001 < abs(numeric) < 1000.0
            )
            if not ok:
                return {"valid": False, "coherence_score": 0.0}

            score = min(abs(float(numeric)) / 55.0, 1.0)
            position.symbolic_coherence = score

            rec = self._recommend(score, position, portfolio_context)
            self.logger.info(
                f"[SE41] position {position.symbol} coherence={score:.3f} rec={rec}"
            )

            return {
                "valid": True,
                "coherence_score": score,
                "symbolic_result": float(numeric),
                "position_recommendation": rec,
                "risk_adjusted_score": score * (1.0 - 0.3 * port_risk),
                "maintain_position": score >= 0.5,
                "validation_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Position validation failed: {e}")
            return {"valid": False, "coherence_score": 0.0, "error": str(e)}

    def _recommend(self, score: float, position: Position, ctx: Dict[str, Any]) -> str:
        pnl_ratio = 0.0
        if position.cost_basis:
            pnl_ratio = position.unrealized_pnl / max(abs(position.cost_basis), 1000.0)

        risk_level = float(ctx.get("risk_level", 0.5))

        if score >= 0.8 and pnl_ratio >= 0.02:
            return "hold_strong"
        if score >= 0.7 and pnl_ratio >= 0.0:
            return "hold"
        if score >= 0.6:
            if pnl_ratio >= 0.05:
                return "reduce_position"
            if pnl_ratio <= -0.03:
                return "close_position"
            return "monitor_closely"
        if score >= 0.4:
            if pnl_ratio <= -0.02 or risk_level >= 0.7:
                return "reduce_position"
            return "monitor_closely"
        return "close_position"


# --------------------------- quantum risk assessor --------------------------


class QuantumRiskAssessment:
    """Light quantum-style risk synthesis for position context."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.QuantumRiskAssessment")

    def assess_position_risk(
        self, position: Position, market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            vol = float(market_data.get("volatility", 0.2))
            corr = float(market_data.get("market_correlation", 0.5))
            liq = float(market_data.get("liquidity", 0.7))

            size_risk = min(abs(position.quantity) / 50000.0, 1.0)
            time_risk = min(
                max(position.holding_period_hours, 0.0) / 720.0, 1.0
            )  # 30d window
            pnl_risk = abs(position.unrealized_pnl) / max(
                abs(position.cost_basis), 1000.0
            )

            q_unc = random.uniform(0.85, 1.15)
            coh = max(position.symbolic_coherence, 0.0)

            market_risk = (vol * 0.4 + (1.0 - liq) * 0.3 + corr * 0.3) * q_unc
            position_risk = (size_risk * 0.5 + time_risk * 0.3 + pnl_risk * 0.2) * (
                2.0 - coh
            )

            total = min(market_risk * 0.6 + position_risk * 0.4, 1.0)
            position.risk_score = total

            category = (
                "minimal"
                if total <= 0.2
                else (
                    "low"
                    if total <= 0.4
                    else (
                        "moderate"
                        if total <= 0.6
                        else "high" if total <= 0.8 else "extreme"
                    )
                )
            )

            recs = self._recommendations(position, total)
            self.logger.info(
                f"[Quantum] risk {position.symbol}: {category} ({total:.3f})"
            )

            return {
                "total_risk_score": total,
                "market_risk": market_risk,
                "position_risk": position_risk,
                "risk_category": category,
                "recommendations": recs,
                "quantum_uncertainty": q_unc,
                "assessment_timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Risk assessment failed: {e}")
            return {"total_risk_score": 0.5, "risk_category": "moderate"}

    def _recommendations(self, position: Position, risk: float) -> List[str]:
        out: List[str] = []
        if risk >= 0.8:
            out += [
                "immediate_position_review",
                "consider_stop_loss_tightening",
                "reduce_position_size",
            ]
        elif risk >= 0.6:
            out += [
                "monitor_closely",
                "review_stop_loss_levels",
                "assess_correlation_exposure",
            ]
        elif risk >= 0.4:
            out += ["standard_monitoring", "periodic_review"]
        else:
            out += ["maintain_current_strategy"]

        if position.unrealized_pnl < -abs(position.cost_basis) * 0.1:
            out.append("review_exit_strategy")
        if position.holding_period_hours > 168:
            out.append("evaluate_profit_taking")
        return out


# --------------------------- PositionManager -------------------------------


class PositionManager:
    """
    EidollonaONE Position Manager (SE41 v4.1+)
    - Adds/updates/closes positions with bounded symbolic validation and light quantum risk.
    - Computes portfolio context for gating (risk level, diversification, exposure).
    """

    def __init__(self, manager_directory: Optional[str] = None):
        self.logger = logging.getLogger(f"{__name__}.PositionManager")

        self.manager_directory = Path(manager_directory or "position_manager_data")
        self.manager_directory.mkdir(exist_ok=True)

        self.validator = SymbolicPositionValidator()
        self.risk_assessor = QuantumRiskAssessment()

        self.positions: Dict[str, Position] = {}
        self.position_history: Dict[str, Position] = {}
        self.portfolio_summary = PositionSummary()

        # Policy limits
        self.max_positions_per_symbol = 3
        self.max_total_positions = 50
        self.max_portfolio_risk = 0.8
        self.rebalance_frequency_hours = 6

        self.logger.info("Position Manager v4.1+ initialized (symbolic✓ quantum✓)")

    # ---- lifecycle ---------------------------------------------------------

    async def add_position(
        self, trade_execution: TradeExecution, market_data: Dict[str, Any]
    ) -> Position:
        """Create a new position from an execution and run validation/risk checks."""
        try:
            pos = Position(
                position_id=f"pos_{int(time.time())}_{uuid.uuid4().hex[:8]}",
                symbol=trade_execution.symbol,
                position_type=(
                    PositionType.LONG
                    if str(trade_execution.trade_type).lower() in ("buy", "option_buy")
                    else PositionType.SHORT
                ),
                quantity=float(trade_execution.position_size),
                entry_price=float(trade_execution.executed_price),
                current_price=float(trade_execution.executed_price),
                cost_basis=float(trade_execution.executed_price)
                * float(trade_execution.position_size),
                fees_paid=float(getattr(trade_execution, "fees", 0.0)),
                quantum_probability=0.8,
            )
            pos.market_value = pos.quantity * pos.current_price

            ctx = self._portfolio_context()
            v = self.validator.validate_position_coherence(pos, ctx)
            r = self.risk_assessor.assess_position_risk(pos, market_data)

            # store & summarize (even if flagged, caller can decide next action)
            self.positions[pos.position_id] = pos
            await self._update_portfolio_summary()

            self.logger.info(
                f"[Add] {pos.symbol} {pos.position_type.value} qty={pos.quantity} @ {pos.entry_price:.2f}"
            )
            return pos
        except Exception as e:
            self.logger.error(f"Position addition failed: {e}")
            raise

    async def update_position_prices(
        self, market_data_batch: Dict[str, Dict[str, Any]]
    ) -> None:
        """Mark all active positions to latest prices and re-evaluate soft constraints."""
        try:
            for pos in list(self.positions.values()):
                if pos.status != PositionStatus.ACTIVE:
                    continue
                data = market_data_batch.get(pos.symbol)
                if not data:
                    continue

                old = pos.current_price
                pos.current_price = float(data.get("current_price", pos.current_price))
                pos.market_value = pos.quantity * pos.current_price

                if pos.position_type == PositionType.LONG:
                    pos.unrealized_pnl = (
                        pos.current_price - pos.entry_price
                    ) * pos.quantity
                else:
                    pos.unrealized_pnl = (
                        pos.entry_price - pos.current_price
                    ) * pos.quantity

                pos.holding_period_hours = (
                    datetime.now() - pos.entry_time
                ).total_seconds() / 3600.0
                pos.volatility_exposure = float(data.get("volatility", 0.2))

                pos.max_profit = max(pos.max_profit, pos.unrealized_pnl)
                pos.max_loss = min(pos.max_loss, pos.unrealized_pnl)
                pos.last_update = datetime.now()

                await self._check_exit_conditions(pos, data)

            await self._update_portfolio_summary()
        except Exception as e:
            self.logger.error(f"Position price update failed: {e}")

    async def monitor_positions(
        self, market_data_batch: Dict[str, Dict[str, Any]]
    ) -> None:
        """Run periodic coherence/risk checks and enact recommendations."""
        try:
            ctx = self._portfolio_context()
            for pos in list(self.positions.values()):
                if pos.status != PositionStatus.ACTIVE:
                    continue

                data = market_data_batch.get(pos.symbol, {})
                v = self.validator.validate_position_coherence(pos, ctx)
                r = self.risk_assessor.assess_position_risk(pos, data)

                await self._apply_recommendations(pos, v, r)

            await self._check_portfolio_constraints()
        except Exception as e:
            self.logger.error(f"Position monitoring failed: {e}")

    # ---- internal actions --------------------------------------------------

    async def _check_exit_conditions(self, pos: Position, md: Dict[str, Any]) -> None:
        try:
            cp = pos.current_price
            close_reason = None

            if pos.stop_loss:
                if (pos.position_type == PositionType.LONG and cp <= pos.stop_loss) or (
                    pos.position_type == PositionType.SHORT and cp >= pos.stop_loss
                ):
                    close_reason = "stop_loss_triggered"

            if pos.take_profit and close_reason is None:
                if (
                    pos.position_type == PositionType.LONG and cp >= pos.take_profit
                ) or (
                    pos.position_type == PositionType.SHORT and cp <= pos.take_profit
                ):
                    close_reason = "take_profit_triggered"

            if pos.risk_score >= 0.9 and close_reason is None:
                close_reason = "excessive_risk"

            if pos.holding_period_hours > 720 and close_reason is None:  # 30 days
                close_reason = "time_limit_exceeded"

            if close_reason:
                await self.close_position(pos.position_id, close_reason)
        except Exception as e:
            self.logger.error(f"Exit condition check failed: {e}")

    async def _apply_recommendations(
        self, pos: Position, v: Dict[str, Any], r: Dict[str, Any]
    ) -> None:
        try:
            rec = v.get("position_recommendation", "monitor_closely")
            if rec == "close_position":
                await self.close_position(
                    pos.position_id, "symbolic_validation_failure"
                )
            elif rec == "reduce_position":
                await self._reduce_position(pos, 0.5)

            risk_recs: List[str] = r.get("recommendations", [])
            if "consider_stop_loss_tightening" in risk_recs:
                await self._tighten_stop_loss(pos)
            if "reduce_position_size" in risk_recs:
                await self._reduce_position(pos, 0.3)
            if "immediate_position_review" in risk_recs:
                self.logger.warning(f"[ATTN] Immediate review suggested: {pos.symbol}")
        except Exception as e:
            self.logger.error(f"Recommendation processing failed: {e}")

    async def close_position(self, position_id: str, reason: str) -> Optional[Position]:
        try:
            pos = self.positions.get(position_id)
            if not pos:
                return None

            if pos.position_type == PositionType.LONG:
                final_pnl = (pos.current_price - pos.entry_price) * pos.quantity
            else:
                final_pnl = (pos.entry_price - pos.current_price) * pos.quantity

            pos.realized_pnl = final_pnl - pos.fees_paid
            pos.status = PositionStatus.CLOSED
            pos.last_update = datetime.now()

            self.position_history[position_id] = pos
            del self.positions[position_id]

            await self._update_portfolio_summary()
            self.logger.info(
                f"[Close] {pos.symbol} {pos.position_type.value} pnl={pos.realized_pnl:.2f} reason={reason}"
            )
            return pos
        except Exception as e:
            self.logger.error(f"Position closure failed: {e}")
            return None

    async def _reduce_position(self, pos: Position, fraction: float) -> None:
        """Reduce position size by fraction (0..1)."""
        try:
            fraction = max(0.0, min(fraction, 1.0))
            if fraction <= 0.0 or pos.quantity == 0.0:
                return
            reduce_qty = pos.quantity * fraction
            # mark‐to‐market realized pnl on reduced slice
            if pos.position_type == PositionType.LONG:
                realized = (pos.current_price - pos.entry_price) * reduce_qty
            else:
                realized = (pos.entry_price - pos.current_price) * reduce_qty
            pos.realized_pnl += realized
            pos.quantity -= reduce_qty
            pos.market_value = pos.quantity * pos.current_price
            pos.cost_basis = pos.entry_price * pos.quantity
            pos.last_update = datetime.now()
            self.logger.info(
                f"[Reduce] {pos.symbol} -{fraction:.0%} qty now {pos.quantity:.2f}"
            )
        except Exception as e:
            self.logger.error(f"Reduce position failed: {e}")

    async def _tighten_stop_loss(self, pos: Position) -> None:
        """Tighten stop based on recent gains; very simple rule."""
        try:
            if pos.position_type == PositionType.LONG:
                new_sl = pos.current_price * 0.97  # 3% trail
                if pos.stop_loss is None or new_sl > pos.stop_loss:
                    pos.stop_loss = new_sl
            else:
                new_sl = pos.current_price * 1.03
                if pos.stop_loss is None or new_sl < pos.stop_loss:
                    pos.stop_loss = new_sl
            pos.last_update = datetime.now()
            self.logger.info(
                f"[Stop] {pos.symbol} tightened stop to {pos.stop_loss:.4f}"
            )
        except Exception as e:
            self.logger.error(f"Tighten stop failed: {e}")

    # ---- portfolio context & summary --------------------------------------

    def _portfolio_context(self) -> Dict[str, Any]:
        try:
            total_value = sum(p.market_value for p in self.positions.values())
            weighted_risk = sum(
                p.risk_score * p.market_value for p in self.positions.values()
            )
            avg_risk = (weighted_risk / total_value) if total_value > 0 else 0.0
            unique_symbols = len(set(p.symbol for p in self.positions.values()))
            diversification = min(unique_symbols / 10.0, 1.0)
            exposure = min(total_value / 1_000_000.0, 1.0)
            return {
                "total_positions": len(self.positions),
                "total_value": total_value,
                "risk_level": avg_risk,
                "diversification": diversification,
                "total_exposure": exposure,
            }
        except Exception as e:
            self.logger.error(f"Portfolio context calc failed: {e}")
            return {"risk_level": 0.5, "diversification": 0.5, "total_exposure": 0.5}

    async def _update_portfolio_summary(self) -> None:
        try:
            active = [
                p for p in self.positions.values() if p.status == PositionStatus.ACTIVE
            ]
            s = self.portfolio_summary
            s.total_positions = len(active)
            s.long_positions = len(
                [p for p in active if p.position_type == PositionType.LONG]
            )
            s.short_positions = len(
                [p for p in active if p.position_type == PositionType.SHORT]
            )
            s.total_market_value = sum(p.market_value for p in active)
            s.total_unrealized_pnl = sum(p.unrealized_pnl for p in active)
            s.total_realized_pnl = sum(
                p.realized_pnl for p in self.position_history.values()
            )
            s.total_fees = sum(p.fees_paid for p in active)
            if active:
                s.average_symbolic_coherence = sum(
                    p.symbolic_coherence for p in active
                ) / len(active)
                total_value = max(s.total_market_value, 1.0)
                s.portfolio_risk_score = (
                    sum(p.risk_score * p.market_value for p in active) / total_value
                )
                s.diversification_score = min(
                    len(set(p.symbol for p in active)) / 15.0, 1.0
                )
        except Exception as e:
            self.logger.error(f"Portfolio summary update failed: {e}")


# ---- factory & smoke -------------------------------------------------------


def create_position_manager(**kwargs) -> PositionManager:
    return PositionManager(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 70)
    print("EidollonaONE Position Manager v4.1+ — bounded • coherent • auditable")
    print("=" * 70)
    mgr = create_position_manager()
    print("✓ ready")
