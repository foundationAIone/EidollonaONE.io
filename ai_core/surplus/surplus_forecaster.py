"""Surplus Forecaster (SE41)

What
----
Forecasts future treasury surplus (revenues - expenses) using exponential
smoothing with governance-adjusted confidence bands.

Why
---
1. Provides proactive visibility into capital runway.
2. Adjusts confidence interval width for risk / uncertainty.
3. Supplies downstream allocators with near-term expectation context.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Sequence, SupportsFloat
import math

try:  # pragma: no cover
    from symbolic_core.symbolic_equation import SymbolicEquation41, SE41Signals  # type: ignore
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
except Exception:  # fallback

    class SE41Signals:  # type: ignore
        def __init__(self, risk=0.3, uncertainty=0.3, coherence=0.8):
            self.risk = risk
            self.uncertainty = uncertainty
            self.coherence = coherence

    class SymbolicEquation41:  # type: ignore
        def evaluate(self, ctx):
            return SE41Signals(
                ctx.get("risk_hint", 0.3),
                ctx.get("uncertainty_hint", 0.3),
                ctx.get("coherence_hint", 0.8),
            )

    def assemble_se41_context(**kw):
        return kw


@dataclass
class SurplusForecast:
    forecast: List[float]
    lower: List[float]
    upper: List[float]
    se41: SE41Signals
    explain: str


class SurplusForecaster:
    def __init__(
        self, alpha: float = 0.35, symbolic: Optional[SymbolicEquation41] = None
    ) -> None:
        self.alpha = max(0.01, min(0.9, alpha))
        self.symbolic = symbolic or SymbolicEquation41()

    def forecast(
        self,
        revenues: Sequence[SupportsFloat],
        expenses: Sequence[SupportsFloat],
        steps: int = 6,
    ) -> SurplusForecast:
        rev_series = [float(v) for v in revenues]
        exp_series = [float(v) for v in expenses]
        n = min(len(rev_series), len(exp_series))
        if n == 0:
            raise ValueError("Need revenue & expense history")
        rev = rev_series[-n:]
        exp = exp_series[-n:]
        series = [r - e for r, e in zip(rev, exp)]
        level = series[0]
        residuals: List[float] = []
        for v in series[1:]:
            level = self.alpha * v + (1 - self.alpha) * level
            residuals.append(v - level)
        variance = (
            (sum(r * r for r in residuals) / len(residuals)) if residuals else 0.0
        )
        vol = math.sqrt(variance)
        risk_hint = min(0.8, 0.15 + vol * 0.6)
        uncertainty_hint = min(
            0.85, 0.2 + (vol * 0.5) + (0.05 if len(series) < 5 else 0)
        )
        coherence_hint = max(0.3, 0.9 - vol * 0.5)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
            )
        )
        # Confidence width grows with risk/uncertainty, shrinks with coherence
        width_factor = 1 + se.risk * 0.7 + se.uncertainty * 0.6 - se.coherence * 0.4
        f = []
        lower = []
        upper = []
        current = level
        for _ in range(steps):
            current = current  # level stays (simple ES)
            band = vol * width_factor
            f.append(current)
            lower.append(current - band)
            upper.append(current + band)
        explain = f"vol={vol:.3f} width_factor={width_factor:.2f} risk={se.risk:.2f} unc={se.uncertainty:.2f} coh={se.coherence:.2f}"
        return SurplusForecast(f, lower, upper, se, explain)


__all__ = ["SurplusForecaster", "SurplusForecast"]


def _selftest() -> int:  # pragma: no cover
    rev = [100, 105, 110, 108, 112, 115]
    exp = [60, 62, 63, 65, 66, 67]
    sf = SurplusForecaster()
    fc = sf.forecast(rev, exp, 3)
    assert len(fc.forecast) == 3
    print("SurplusForecaster selftest", fc.explain)
    return 0


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(_selftest())
