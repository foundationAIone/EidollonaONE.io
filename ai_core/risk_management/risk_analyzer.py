"""Composite Risk Analyzer (SE41)

What
----
Aggregates VaR, Tail Risk, Stress, and Compliance signals into unified SE41
snapshot. Provides combined stability & meta diagnostic explanation.

Why
---
1. Holistic risk governance vs siloed metrics.
2. Captures interplay (e.g., moderate VaR + extreme tail heaviness).
3. Produces single stability scalar for gating strategy risk budgets.
4. Deterministic weighting allows reproducible CI validation.
"""

from __future__ import annotations
from typing import Dict, Any, Optional

from .value_at_risk import VaREngine
from .tail_risk import TailRiskEngine
from .stress_testing import StressTester, Position
from .compliance_engine import ComplianceEngine

try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41  # type: ignore
except Exception:  # pragma: no cover
    from .value_at_risk import SymbolicEquation41  # type: ignore

try:  # pragma: no cover
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    def assemble_se41_context(**kw):
        return kw


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


class RiskAnalyzer:
    def __init__(self, symbolic: Optional[Any] = None) -> None:
        self.var_engine = VaREngine(symbolic=symbolic)
        self.tail_engine = TailRiskEngine(symbolic=symbolic)
        self.stress_tester = StressTester(symbolic=symbolic)
        self.compliance = ComplianceEngine(symbolic=symbolic)
        self.symbolic = symbolic or SymbolicEquation41()

    def push_return(self, r: float) -> None:
        self.var_engine.push(r)
        self.tail_engine.push_return(r)

    def add_position(
        self,
        symbol: str,
        value: float,
        beta: float = 1.0,
        delta: float = 1.0,
        vega: float = 0.0,
    ) -> None:
        self.stress_tester.add_position(Position(symbol, value, beta, delta, vega))

    def snapshot(self) -> Dict[str, Any]:
        s_var = self.var_engine.snapshot_dict()
        s_tail = self.tail_engine.snapshot_dict()
        s_stress = self.stress_tester.snapshot_dict()
        gross = sum(p.value for p in self.stress_tester.positions)
        leverage = (
            gross / max(1.0, gross * 0.5) if gross else 0.0
        )  # placeholder leverage heuristic
        s_comp = self.compliance.snapshot_dict(
            [
                {"symbol": p.symbol, "value": p.value}
                for p in self.stress_tester.positions
            ],
            gross_exposure=gross,
            leverage=leverage,
            var_99=s_var.get("hist_var_99", 0) * gross,
            worst_stress_loss=s_stress.get("worst_loss", 0),
        )
        risks = [
            s_var["se41"]["risk"],
            s_tail["se41"]["risk"],
            s_stress["se41"]["risk"],
            s_comp["se41"]["risk"],
        ]
        uncs = [
            s_var["se41"]["uncertainty"],
            s_tail["se41"]["uncertainty"],
            s_stress["se41"]["uncertainty"],
            s_comp["se41"]["uncertainty"],
        ]
        cohs = [
            s_var["se41"]["coherence"],
            s_tail["se41"]["coherence"],
            s_stress["se41"]["coherence"],
            s_comp["se41"]["coherence"],
        ]
        risk_hint = sum(risks) / len(risks)
        uncertainty_hint = sum(uncs) / len(uncs)
        coherence_hint = sum(cohs) / len(cohs)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={"risk": {"engines": 4}},
            )
        )
        stability = _clamp01(1 - (se.risk + se.uncertainty) / 2.0)
        return {
            "var": s_var,
            "tail": s_tail,
            "stress": s_stress,
            "compliance": s_comp,
            "se41": {
                "risk": se.risk,
                "uncertainty": se.uncertainty,
                "coherence": se.coherence,
            },
            "stability": stability,
        }


def _selftest() -> int:  # pragma: no cover
    import random

    ra = RiskAnalyzer()
    for _ in range(600):
        ra.push_return(random.gauss(0, 0.01))
    ra.add_position("AAA", 500_000, beta=1.1, vega=120)
    ra.add_position("BBB", 300_000, beta=0.9, vega=0)
    snap = ra.snapshot()
    assert "stability" in snap
    print("RiskAnalyzer selftest", snap["stability"])
    return 0


__all__ = ["RiskAnalyzer"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    ra = RiskAnalyzer()
    import random

    for _ in range(500):
        ra.push_return(random.gauss(0, 0.012))
    ra.add_position("X", 300_000, vega=50)
    print(json.dumps(ra.snapshot(), indent=2))
