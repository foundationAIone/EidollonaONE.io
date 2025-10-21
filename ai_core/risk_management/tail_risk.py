"""Tail Risk & Extreme Value Approximation (SE41)

What
----
Approximates tail heaviness via Hill estimator and conditional tail expectation
on exceedances above a high quantile threshold.

Why
---
1. Captures distribution shape missed by simple VaR.
2. Fat tails elevate uncertainty & risk gating.
3. Stability improves when tail index (alpha) indicates thinner tails.
4. Lightweight EVT approximation suitable for real-time monitoring.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Deque, Dict, Any, Optional
from collections import deque
import math

try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41, SE41Signals  # type: ignore
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
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
class TailSnapshot:
    tail_index: float
    mean_excess: float
    threshold: float
    exceedance_ratio: float
    severity: float
    stability: float
    se41: SE41Signals
    explain: str


class TailRiskEngine:
    def __init__(
        self,
        window: int = 3000,
        quantile: float = 0.9,
        symbolic: Optional[SymbolicEquation41] = None,
    ) -> None:
        self.window = max(500, window)
        self.losses: Deque[float] = deque()  # positive losses
        self.q = quantile
        self.symbolic = symbolic or SymbolicEquation41()

    def push_return(self, r: float) -> None:
        if r < 0:
            self.losses.append(-r)
            if len(self.losses) > self.window:
                self.losses.popleft()

    def simulate_random(self, n: int = 1200, vol: float = 0.01) -> None:
        import random

        for _ in range(n):
            r = random.gauss(0, vol)
            # occasional jump
            if random.random() < 0.01:
                r -= abs(random.gauss(0, vol * 8))
            self.push_return(r)

    def snapshot(self) -> TailSnapshot:
        if len(self.losses) < 100:
            se = self.symbolic.evaluate(
                assemble_se41_context(
                    risk_hint=0.3, uncertainty_hint=0.5, coherence_hint=0.5
                )
            )
            return TailSnapshot(0, 0, 0, 0, 0, 1.0, se, "insufficient")
        arr = sorted(self.losses)
        k = int(self.q * len(arr))
        k = min(len(arr) - 2, max(5, k))
        threshold = arr[k]
        exceed = [x for x in arr if x >= threshold]
        exceed_ratio = len(exceed) / len(arr)
        # Hill estimator on exceedances above threshold (largest m values)
        m = len(exceed)
        if m < 5:
            tail_index = 0.0
        else:
            xm = threshold
            logs = [math.log(x / xm) for x in exceed if x > xm]
            tail_index = (len(logs) / (sum(logs) + 1e-12)) if logs else 0.0
        mean_excess = (sum(exceed) / m - threshold) if m > 0 else 0.0
        severity = mean_excess * exceed_ratio
        # Governance mapping
        risk_hint = _clamp01(0.12 + severity * 0.8)
        uncertainty_hint = _clamp01(
            0.2 + (1 / (tail_index + 1e-6)) * 0.05 if tail_index > 0 else 0.6
        )
        coherence_hint = _clamp01(0.85 - uncertainty_hint * 0.6)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={"tail": {"alpha": tail_index}},
            )
        )
        stability = _clamp01(1 - (se.risk + se.uncertainty) / 2.0)
        explain = f"alpha={tail_index:.2f} sev={severity:.4f} thr={threshold:.4f}"
        return TailSnapshot(
            tail_index,
            mean_excess,
            threshold,
            exceed_ratio,
            severity,
            stability,
            se,
            explain,
        )

    def snapshot_dict(self) -> Dict[str, Any]:
        s = self.snapshot()
        return {
            "tail_index": s.tail_index,
            "mean_excess": s.mean_excess,
            "threshold": s.threshold,
            "exceedance_ratio": s.exceedance_ratio,
            "severity": s.severity,
            "stability": s.stability,
            "se41": {
                "risk": s.se41.risk,
                "uncertainty": s.se41.uncertainty,
                "coherence": s.se41.coherence,
            },
            "explain": s.explain,
        }


def _selftest() -> int:  # pragma: no cover
    tr = TailRiskEngine()
    tr.simulate_random()
    d = tr.snapshot_dict()
    assert "tail_index" in d
    print("TailRiskEngine selftest", d["tail_index"])
    return 0


__all__ = ["TailRiskEngine", "TailSnapshot"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    tr = TailRiskEngine()
    tr.simulate_random()
    print(json.dumps(tr.snapshot_dict(), indent=2))
