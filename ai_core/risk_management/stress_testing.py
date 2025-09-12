"""Stress Testing Engine (SE41)

What
----
Defines canonical stress scenarios (rate shock, volatility spike, gap down, correlation breakdown)
and applies them to a simplified portfolio of positions with greeks/betas.

Why
---
1. Exposes non-linear drawdowns under adverse but plausible conditions.
2. Scenario dispersion vs baseline adds uncertainty when large.
3. Worst-case loss escalates risk hint gating.
4. Supports governance snapshots for oversight & capital buffers.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import math

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
        def evaluate(self, ctx):
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
class Position:
    symbol: str
    value: float  # notional
    beta: float = 1.0
    delta: float = 1.0
    vega: float = 0.0


@dataclass
class StressResult:
    worst_loss: float
    average_loss: float
    dispersion: float
    scenario_losses: Dict[str, float]
    stability: float
    se41: SE41Signals
    explain: str


class StressTester:
    def __init__(self, symbolic: Optional[SymbolicEquation41] = None) -> None:
        self.positions: List[Position] = []
        self.symbolic = symbolic or SymbolicEquation41()

    def add_position(self, pos: Position) -> None:
        self.positions.append(pos)

    # Scenario definitions return percentage loss relative to value
    def _scenarios(self) -> Dict[str, Any]:
        return {
            "rate_shock": lambda p: 0.03 * p.beta,  # 300bp parallel shift
            "vol_spike": lambda p: max(0.0, -0.5 * p.vega / 100.0)
            + 0.015 * abs(p.vega),
            "gap_down": lambda p: 0.08 * p.delta,  # 8% immediate gap
            "corr_break": lambda p: 0.05 * (1 + abs(p.beta - p.delta) / 2.0),
        }

    def run(self) -> StressResult:
        if not self.positions:
            se = self.symbolic.evaluate(
                assemble_se41_context(
                    risk_hint=0.3, uncertainty_hint=0.4, coherence_hint=0.6
                )
            )
            return StressResult(0, 0, 0, {}, 1.0, se, "empty")
        scenarios = self._scenarios()
        scenario_losses: Dict[str, float] = {}
        for name, fn in scenarios.items():
            loss = 0.0
            for pos in self.positions:
                pct = fn(pos)
                loss += pos.value * pct
            scenario_losses[name] = loss
        losses = list(scenario_losses.values())
        worst = max(losses)
        avg = sum(losses) / len(losses)
        mean = avg
        dispersion = (
            math.sqrt(sum((l - mean) ** 2 for l in losses) / len(losses))
            / (mean + 1e-9)
            if mean > 0
            else 0.0
        )
        risk_hint = _clamp01(0.1 + worst / (sum(p.value for p in self.positions) * 0.5))
        uncertainty_hint = _clamp01(0.15 + dispersion * 0.7)
        coherence_hint = _clamp01(0.9 - dispersion * 0.7)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={"stress": {"worst": worst}},
            )
        )
        stability = _clamp01(1 - (se.risk + se.uncertainty) / 2.0)
        explain = f"worst={worst:.2f} disp={dispersion:.2f}"
        return StressResult(
            worst, avg, dispersion, scenario_losses, stability, se, explain
        )

    def snapshot_dict(self) -> Dict[str, Any]:
        r = self.run()
        return {
            "worst_loss": r.worst_loss,
            "average_loss": r.average_loss,
            "dispersion": r.dispersion,
            "scenarios": r.scenario_losses,
            "stability": r.stability,
            "se41": {
                "risk": r.se41.risk,
                "uncertainty": r.se41.uncertainty,
                "coherence": r.se41.coherence,
            },
            "explain": r.explain,
        }


def _selftest() -> int:  # pragma: no cover
    st = StressTester()
    st.add_position(Position("ABC", 1_000_000, beta=1.1, delta=1.0, vega=150))
    d = st.snapshot_dict()
    assert "worst_loss" in d
    print("StressTester selftest", d["worst_loss"])
    return 0


__all__ = ["StressTester", "Position", "StressResult"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    st = StressTester()
    st.add_position(Position("XYZ", 500_000, beta=0.8, delta=1.0, vega=50))
    st.add_position(Position("FUT", 700_000, beta=1.2, delta=1.0, vega=0))
    print(json.dumps(st.snapshot_dict(), indent=2))
