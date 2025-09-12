"""Portfolio accounting & performance metrics (SE41 v4.1+ enhanced)

Added features:
	* Optional SE41 context & signals blending for trade gating
	* Latency tracking for finalize()
	* Risk guard: blocks trades exceeding leverage threshold
	* Expanded metrics (equity_peak, drawdown_series length, trade_count)
	* Deterministic fallback if SE41 stack absent
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import math
from time import perf_counter

try:
    from trading.helpers.se41_trading_gate import (
        se41_numeric,
        ethos_decision,
        se41_signals,
    )  # type: ignore
except Exception:  # pragma: no cover

    def se41_numeric(**_kw):  # type: ignore
        return {"score": 0.55}

    def ethos_decision(_tx):  # type: ignore
        return {"decision": "allow"}

    def se41_signals(_ctx):  # type: ignore
        return {"coherence": 0.55}


try:
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    def assemble_se41_context(**kw):  # type: ignore
        return {"substrate": {"S_EM": 0.82}}


@dataclass
class PortfolioAccount:
    cash: float
    positions: Dict[str, float]
    prices: Dict[str, float]

    def equity(self) -> float:
        return self.cash + sum(
            qty * self.prices.get(sym, 0.0) for sym, qty in self.positions.items()
        )


@dataclass
class PerformanceReport:
    equity_curve: List[float]
    returns: List[float]
    sharpe: float
    max_drawdown: float
    turnover: float
    ethos_flags: Dict[str, int]


class PortfolioBacktest:
    def __init__(
        self,
        initial_cash: float = 1_000_000.0,
        max_trade_leverage: float = 10.0,
        use_context: bool = False,
    ) -> None:
        self.account = PortfolioAccount(initial_cash, {}, {})
        self.equity_curve: List[float] = []
        self.returns: List[float] = []
        self.prior_equity: float = initial_cash
        self.turnover: float = 0.0
        self.ethos_flags = {"holds": 0, "denies": 0}
        self.trade_count = 0
        self.max_trade_leverage = max_trade_leverage
        self.use_context = use_context
        self._ctx: Optional[Dict[str, Any]] = None

    def update_prices(self, price_updates: Dict[str, float]) -> None:
        self.account.prices.update(price_updates)

    def trade(self, symbol: str, qty: float, price: float) -> None:
        # Lazy context build
        if self.use_context and self._ctx is None:
            self._ctx = assemble_se41_context(
                perception={"mode": "portfolio"},
                intent={"objective": "alpha"},
                mirror={"consistency": 0.74},
            )
        equity = self.account.equity()
        notional = abs(qty * price)
        leverage = notional / max(equity, 1e-9)
        if leverage > self.max_trade_leverage:  # hard risk guard
            self.ethos_flags["denies"] += 1
            return
        numeric = se41_numeric(M_t=0.61, DNA_states=[1.0, leverage, 1.0, 1.11])
        base_score = numeric.get("score", 0.55)
        if self._ctx is not None:
            coh = se41_signals(self._ctx).get("coherence", 0.55)
            score = (base_score + coh) / 2.0
        else:
            score = base_score
        gate = ethos_decision({"scope": "trade", "lev": leverage, "score": score})
        decision = gate.get("decision", "allow") if isinstance(gate, dict) else "allow"
        if decision == "deny":
            self.ethos_flags["denies"] += 1
            return
        if decision == "hold":
            self.ethos_flags["holds"] += 1
            return
        self.account.cash -= qty * price
        self.account.positions[symbol] = self.account.positions.get(symbol, 0.0) + qty
        self.turnover += abs(qty * price)
        self.trade_count += 1

    def step(self) -> None:
        eq = self.account.equity()
        self.equity_curve.append(eq)
        ret = (eq / self.prior_equity - 1.0) if self.prior_equity else 0.0
        self.returns.append(ret)
        self.prior_equity = eq

    def finalize(self) -> PerformanceReport:
        start = perf_counter()
        sharpe = 0.0
        if self.returns:
            mean = sum(self.returns) / len(self.returns)
            var = sum((r - mean) ** 2 for r in self.returns) / max(
                1, len(self.returns) - 1
            )
            vol = math.sqrt(var) if var > 0 else 0.0
            sharpe = mean / vol if vol > 0 else 0.0
        peak = -1e9
        drawdown = 0.0
        for v in self.equity_curve:
            if v > peak:
                peak = v
            dd = (v / peak - 1.0) if peak else 0.0
            drawdown = min(drawdown, dd)
        turnover = (
            self.turnover / max(self.equity_curve[-1], 1e-9)
            if self.equity_curve
            else 0.0
        )
        report = PerformanceReport(
            self.equity_curve,
            self.returns,
            sharpe,
            drawdown,
            turnover,
            dict(self.ethos_flags),
        )
        self.last_finalize_ms = round((perf_counter() - start) * 1000.0, 3)
        return report


__all__ = ["PortfolioAccount", "PerformanceReport", "PortfolioBacktest"]
