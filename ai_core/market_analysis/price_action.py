"""Price Action & Regime Classification (SE41)

What
----
Detects swing highs/lows, structural breaks, volatility regimes, and classifies
market state (trend, mean-revert, volatile consolidation). Provides governance
hints based on structural clarity vs fragmentation.

Why
---
1. Execution alignment: Trend regime supports breakout continuation strategies.
2. Risk gating: Regime shifts or low-structure fragments raise uncertainty.
3. Coherence: Clean higher-high sequence or balanced oscillation improves coherence.
4. Strategy selection: Distinct regime labeling facilitates adaptive model weighting.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Deque
from collections import deque
import math
import random

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
class PriceActionSnapshot:
    regime: str
    swing_count: int
    structure_score: float
    volatility: float
    trend_strength: float
    stability: float
    se41: SE41Signals
    explain: str


class PriceActionAnalyzer:
    def __init__(
        self,
        window: int = 400,
        swing_lookback: int = 3,
        symbolic: Optional[SymbolicEquation41] = None,
    ) -> None:
        self.window = max(100, window)
        self.prices: Deque[float] = deque()
        self.swing_lookback = max(2, swing_lookback)
        self.symbolic = symbolic or SymbolicEquation41()
        self.swings: List[float] = []  # Alternating highs/lows
        self.swing_dirs: List[int] = []  # +1 high, -1 low

    def push_price(self, price: float) -> None:
        self.prices.append(price)
        if len(self.prices) > self.window:
            self.prices.popleft()
        self._maybe_swing()

    def simulate_random(self, n: int = 500, base: float = 100.0) -> None:
        p = base
        drift = random.uniform(-0.05, 0.05)
        for _ in range(n):
            p += drift + random.uniform(-0.3, 0.3)
            self.push_price(p)

    def _maybe_swing(self) -> None:
        if len(self.prices) < self.swing_lookback * 2 + 1:
            return
        arr = list(self.prices)
        idx = len(arr) - self.swing_lookback - 1
        window = arr[idx - self.swing_lookback : idx + self.swing_lookback + 1]
        center = window[self.swing_lookback]
        if center == max(window):
            if not self.swing_dirs or self.swing_dirs[-1] != +1:
                self.swings.append(center)
                self.swing_dirs.append(+1)
        elif center == min(window):
            if not self.swing_dirs or self.swing_dirs[-1] != -1:
                self.swings.append(center)
                self.swing_dirs.append(-1)
        if len(self.swings) > 200:
            self.swings = self.swings[-200:]
            self.swing_dirs = self.swing_dirs[-200:]

    def _compute(self) -> PriceActionSnapshot:
        if len(self.prices) < 10:
            se = self.symbolic.evaluate(
                assemble_se41_context(
                    risk_hint=0.4, uncertainty_hint=0.5, coherence_hint=0.5
                )
            )
            return PriceActionSnapshot("insufficient", 0, 0, 0, 0, 1.0, se, "empty")
        arr = list(self.prices)
        returns = [
            math.log(arr[i] / arr[i - 1]) for i in range(1, len(arr)) if arr[i - 1] != 0
        ]
        vol = math.sqrt(sum(r * r for r in returns) / max(1, len(returns))) * math.sqrt(
            252
        )
        # Trend strength via linear regression slope / residual volatility
        n = len(arr)
        x = list(range(n))
        mean_x = (n - 1) / 2
        mean_y = sum(arr) / n
        cov = sum((xi - mean_x) * (arr[i] - mean_y) for i, xi in enumerate(x))
        varx = sum((xi - mean_x) ** 2 for xi in x) + 1e-9
        slope = cov / varx
        residual_var = (
            sum((arr[i] - (mean_y + slope * (x[i] - mean_x))) ** 2 for i in range(n))
            / n
        )
        trend_strength = abs(slope) / math.sqrt(residual_var + 1e-9)
        # Structure score: ratio of alternating swings vs total swings & amplitude consistency
        swing_count = len(self.swings)
        if swing_count >= 4:
            amps = [
                abs(self.swings[i] - self.swings[i - 1]) for i in range(1, swing_count)
            ]
            if amps:
                mean_amp = sum(amps) / len(amps)
                var_amp = sum((a - mean_amp) ** 2 for a in amps) / len(amps)
                cv = math.sqrt(var_amp) / (mean_amp + 1e-9)
                structure_score = _clamp01(1.0 - cv)
            else:
                structure_score = 0.0
        else:
            structure_score = 0.0
        # Regime classification
        if trend_strength > 1.2 and vol < 0.6:
            regime = "steady_trend"
        elif trend_strength > 1.0 and vol >= 0.6:
            regime = "volatile_trend"
        elif structure_score > 0.6 and vol < 0.5:
            regime = "mean_revert"
        elif vol > 1.2 and structure_score < 0.3:
            regime = "chaotic"
        else:
            regime = "transition"
        # Governance hints
        risk_hint = _clamp01(0.15 + (vol / 2.5))
        if regime in ("chaotic", "transition"):
            uncertainty_hint = _clamp01(0.4 + (1 - structure_score) * 0.6)
        else:
            uncertainty_hint = _clamp01(0.2 + (1 - structure_score) * 0.4)
        coherence_hint = _clamp01(
            0.85 - (uncertainty_hint * 0.7) + structure_score * 0.3
        )
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={"price_action": {"regime": regime}},
            )
        )
        stability = _clamp01(1.0 - (se.risk + se.uncertainty) / 2.0)
        explain = f"reg={regime} trend={trend_strength:.2f} vol={vol:.2f} struct={structure_score:.2f}"
        return PriceActionSnapshot(
            regime=regime,
            swing_count=swing_count,
            structure_score=structure_score,
            volatility=vol,
            trend_strength=trend_strength,
            stability=stability,
            se41=se,
            explain=explain,
        )

    def snapshot_dict(self) -> Dict[str, Any]:
        m = self._compute()
        return {
            "regime": m.regime,
            "swing_count": m.swing_count,
            "structure": m.structure_score,
            "volatility": m.volatility,
            "trend_strength": m.trend_strength,
            "stability": m.stability,
            "se41": {
                "risk": m.se41.risk,
                "uncertainty": m.se41.uncertainty,
                "coherence": m.se41.coherence,
            },
            "explain": m.explain,
        }


def _selftest() -> int:  # pragma: no cover
    pa = PriceActionAnalyzer()
    pa.simulate_random(600)
    s = pa.snapshot_dict()
    assert "regime" in s
    print("PriceActionAnalyzer selftest", s["regime"])
    return 0


__all__ = ["PriceActionAnalyzer", "PriceActionSnapshot"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    pa = PriceActionAnalyzer()
    pa.simulate_random(500)
    print(json.dumps(pa.snapshot_dict(), indent=2))
