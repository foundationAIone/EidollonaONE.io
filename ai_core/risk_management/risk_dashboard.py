"""Risk Dashboard Utility (SE41)

What
----
Renders composite risk snapshot (from RiskAnalyzer) into concise dictionary /
ASCII bar representation for logging or CLI review.

Why
---
1. Human oversight: quick qualitative scan.
2. Governance reporting: unify metrics in stable schema.
3. Deterministic formatting for tests.
"""

from __future__ import annotations
from typing import Dict, Any
from .risk_analyzer import RiskAnalyzer


def _bar(value: float, length: int = 20) -> str:
    filled = int(max(0.0, min(1.0, value)) * length)
    return "[" + "#" * filled + "-" * (length - filled) + "]"


class RiskDashboard:
    def __init__(self, analyzer: RiskAnalyzer | None = None) -> None:
        self.analyzer = analyzer or RiskAnalyzer()

    def render(self) -> Dict[str, Any]:
        snap = self.analyzer.snapshot()
        se = snap["se41"]
        return {
            "stability": snap["stability"],
            "bars": {
                "risk": _bar(se["risk"]),
                "uncertainty": _bar(se["uncertainty"]),
                "coherence": _bar(se["coherence"]),
                "stability": _bar(snap["stability"]),
            },
            "var99": snap["var"]["hist_var_99"],
            "tail_alpha": snap["tail"]["tail_index"],
            "worst_stress": snap["stress"]["worst_loss"],
            "breaches": snap["compliance"]["breaches"],
        }


def _selftest() -> int:  # pragma: no cover
    import random

    dash = RiskDashboard()
    for _ in range(400):
        dash.analyzer.push_return(random.gauss(0, 0.01))
    dash.analyzer.add_position("AAA", 200_000)
    r = dash.render()
    assert "stability" in r
    print("RiskDashboard selftest", r["bars"]["risk"])
    return 0


__all__ = ["RiskDashboard"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json
    import random

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    dash = RiskDashboard()
    for _ in range(500):
        dash.analyzer.push_return(random.gauss(0, 0.012))
    dash.analyzer.add_position("X", 100_000)
    print(json.dumps(dash.render(), indent=2))
