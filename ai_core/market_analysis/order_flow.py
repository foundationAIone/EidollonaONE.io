"""Order Flow & Footprint Analytics (SE41)

What
----
Tracks aggressive vs passive volume, cumulative delta, ladder imbalance, and
absorption signals to quantify microstructure pressure.

Why
---
1. Directional conviction: Rising cumulative delta + imbalance supports trend.
2. Reversal / absorption: Large passive volume halting aggressive flow raises uncertainty.
3. Governance: Extreme one-sided pressure elevates risk hint (potential exhaustion).
4. Execution: Provides footprint-style metrics for sizing and entry refinement.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Deque, Tuple
from collections import deque
import random
import time

try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41, SE41Signals  # type: ignore
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    class SE41Signals:
        def __init__(self, risk=0.4, uncertainty=0.4, coherence=0.6):
            self.risk = risk
            self.uncertainty = uncertainty
            self.coherence = coherence

    class SymbolicEquation41:  # type: ignore
        def evaluate(self, ctx: Dict[str, Any]):
            return SE41Signals(
                ctx.get("risk_hint", 0.4),
                ctx.get("uncertainty_hint", 0.4),
                ctx.get("coherence_hint", 0.6),
            )

    def assemble_se41_context(**kw):
        return kw


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class OrderFlowSnapshot:
    cum_delta: float
    delta_rate: float
    imbalance: float
    absorption_score: float
    pressure: float
    stability: float
    se41: SE41Signals
    explain: str


class OrderFlowAnalyzer:
    def __init__(
        self, window: int = 300, symbolic: Optional[SymbolicEquation41] = None
    ) -> None:
        self.window = max(50, window)
        self.trades: Deque[Tuple[float, float, bool]] = (
            deque()
        )  # (price, size, is_aggr_buy)
        self.cum_delta = 0.0
        self.symbolic = symbolic or SymbolicEquation41()
        self.last_eval_time = time.time()
        self._delta_series: Deque[float] = deque(maxlen=50)

    def push_trade(self, price: float, size: float, is_aggressive_buy: bool) -> None:
        self.trades.append((price, size, is_aggressive_buy))
        if is_aggressive_buy:
            self.cum_delta += size
        else:
            self.cum_delta -= size
        if len(self.trades) > self.window:
            old_price, old_size, old_is_buy = self.trades.popleft()
            if old_is_buy:
                self.cum_delta -= old_size
            else:
                self.cum_delta += old_size

    def simulate_random(self, n: int = 400, base: float = 100.0) -> None:
        p = base
        for _ in range(n):
            p += random.uniform(-0.2, 0.2)
            size = random.uniform(0.1, 3.0)
            is_buy = random.random() < 0.5 + (p - base) / 50.0
            self.push_trade(p, size, is_buy)

    def _compute_metrics(self) -> OrderFlowSnapshot:
        if not self.trades:
            se = self.symbolic.evaluate(
                assemble_se41_context(
                    risk_hint=0.4, uncertainty_hint=0.4, coherence_hint=0.6
                )
            )
            return OrderFlowSnapshot(0, 0, 0, 0, 0, 1.0, se, "empty")
        buys = sum(sz for _, sz, is_buy in self.trades if is_buy)
        sells = sum(sz for _, sz, is_buy in self.trades if not is_buy)
        total = buys + sells + 1e-9
        imbalance = (buys - sells) / total  # -1..1
        # Absorption: detect large counterflow on price stagnation
        prices = [p for p, _, _ in self.trades]
        price_range = max(prices) - min(prices)
        counterflow = sells if imbalance > 0 else buys
        absorption_raw = (
            counterflow / total
            if price_range < max(0.05, 0.001 * sum(sz for _, sz, _ in self.trades))
            else 0.0
        )
        # Delta rate (recent slope)
        self._delta_series.append(self.cum_delta)
        if len(self._delta_series) >= 5:
            first = list(self._delta_series)[0]
            last = self._delta_series[-1]
            delta_rate = (last - first) / (len(self._delta_series) - 1)
        else:
            delta_rate = 0.0
        pressure = abs(imbalance) * (1.0 - absorption_raw * 0.5)
        # Governance hints
        risk_hint = _clamp01(0.15 + pressure * 0.6)
        uncertainty_hint = _clamp01(0.2 + absorption_raw * 0.6)
        coherence_hint = _clamp01(0.85 - absorption_raw * 0.5)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={"order_flow": {"imbalance": imbalance}},
            )
        )
        stability = _clamp01(1.0 - (se.risk + se.uncertainty) / 2.0)
        explain = f"imb={imbalance:.2f} abs={absorption_raw:.2f} pr={pressure:.2f}"
        return OrderFlowSnapshot(
            cum_delta=self.cum_delta,
            delta_rate=delta_rate,
            imbalance=imbalance,
            absorption_score=absorption_raw,
            pressure=pressure,
            stability=stability,
            se41=se,
            explain=explain,
        )

    def snapshot_dict(self) -> Dict[str, Any]:
        m = self._compute_metrics()
        return {
            "cum_delta": m.cum_delta,
            "delta_rate": m.delta_rate,
            "imbalance": m.imbalance,
            "absorption": m.absorption_score,
            "pressure": m.pressure,
            "stability": m.stability,
            "se41": {
                "risk": m.se41.risk,
                "uncertainty": m.se41.uncertainty,
                "coherence": m.se41.coherence,
            },
            "explain": m.explain,
        }


def _selftest() -> int:  # pragma: no cover
    of = OrderFlowAnalyzer()
    of.simulate_random(600)
    s = of.snapshot_dict()
    assert "imbalance" in s
    print("OrderFlowAnalyzer selftest", s["imbalance"])
    return 0


__all__ = ["OrderFlowAnalyzer", "OrderFlowSnapshot"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    of = OrderFlowAnalyzer()
    of.simulate_random(400)
    print(json.dumps(of.snapshot_dict(), indent=2))
