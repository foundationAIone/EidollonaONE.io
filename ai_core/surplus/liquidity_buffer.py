"""Liquidity Buffer Model (SE41)

What
----
Determines target liquidity buffer size given projected net outflow
volatility, stress scenarios, and governance (risk / uncertainty) posture.

Why
---
1. Shields operations from cash flow shocks.
2. Dynamically scales buffer with systemic risk.
3. Encourages lean capital use when coherence strong & risk low.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
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
class LiquidityBufferResult:
    target_buffer: float
    stress_p95: float
    se41: SE41Signals
    explain: str


class LiquidityBufferModel:
    def __init__(
        self, days: int = 30, symbolic: Optional[SymbolicEquation41] = None
    ) -> None:
        self.days = days
        self.symbolic = symbolic or SymbolicEquation41()

    def compute(
        self, net_outflows: List[float], stress_multiplier: float = 2.5
    ) -> LiquidityBufferResult:
        if not net_outflows:
            raise ValueError("Need net outflow history (positive = outflow)")
        vols = net_outflows[-self.days :]
        mean = sum(vols) / len(vols)
        var = sum((v - mean) ** 2 for v in vols) / max(1, len(vols) - 1)
        sigma = math.sqrt(var)
        risk_hint = min(0.85, 0.2 + sigma * 0.7)
        uncertainty_hint = min(
            0.9, 0.25 + (sigma * 0.5) + (0.05 if len(vols) < 10 else 0)
        )
        coherence_hint = max(0.25, 0.88 - sigma * 0.45)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
            )
        )
        stress_p95 = mean + 1.65 * sigma
        base_buffer = mean * self.days + sigma * math.sqrt(self.days)
        # Governance scaling
        scale = 1 + se.risk * 0.8 + se.uncertainty * 0.6 - se.coherence * 0.4
        target = (base_buffer + stress_multiplier * stress_p95) * scale
        explain = f"sigma={sigma:.3f} scale={scale:.2f} risk={se.risk:.2f} unc={se.uncertainty:.2f} coh={se.coherence:.2f}"
        return LiquidityBufferResult(target, stress_p95, se, explain)


__all__ = ["LiquidityBufferModel", "LiquidityBufferResult"]


def _selftest() -> int:  # pragma: no cover
    flows = [10, 12, 8, 15, 9, 11, 13, 14, 10, 12, 11, 13]
    model = LiquidityBufferModel()
    res = model.compute(flows)
    assert res.target_buffer > 0
    print("LiquidityBufferModel selftest", res.explain)
    return 0


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(_selftest())
