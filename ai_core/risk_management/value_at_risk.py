"""Value at Risk & Expected Shortfall Engine (SE41)

What
----
Maintains rolling return series to compute historical and parametric (Gaussian / EWMA)
VaR plus Expected Shortfall at multiple confidence levels.

Why
---
1. Core downside risk metric for position sizing & capital allocation.
2. Divergence between parametric and historical indicates regime/ distribution shift (uncertainty).
3. ES (CVaR) supplies tail severity beyond quantile cut.
4. Governance: Elevated VaR or widening model disagreement boosts risk & uncertainty hints.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Deque, Dict, Any, Optional
from collections import deque
import math
import statistics

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


_Z = {0.95: 1.6448536269, 0.99: 2.326347874}  # standard normal quantiles


@dataclass
class VaRSnapshot:
    hist_var_95: float
    hist_var_99: float
    para_var_95: float
    para_var_99: float
    es_95: float
    es_99: float
    disagreement: float
    stability: float
    se41: SE41Signals
    explain: str


class VaREngine:
    def __init__(
        self,
        window: int = 1500,
        decay: float = 0.94,
        symbolic: Optional[SymbolicEquation41] = None,
    ) -> None:
        self.window = max(250, window)
        self.returns: Deque[float] = deque()
        self.decay = decay
        self.ewma_var: Optional[float] = None
        self.symbolic = symbolic or SymbolicEquation41()

    def push(self, r: float) -> None:
        # r: arithmetic daily return (e.g., 0.01 for +1%)
        self.returns.append(r)
        if len(self.returns) > self.window:
            self.returns.popleft()
        # EWMA variance update
        if self.ewma_var is None:
            self.ewma_var = r * r
        else:
            self.ewma_var = self.decay * self.ewma_var + (1 - self.decay) * r * r

    def simulate_random(
        self, n: int = 800, mean: float = 0.0005, vol: float = 0.01
    ) -> None:
        import random

        for _ in range(n):
            self.push(random.gauss(mean, vol))

    def snapshot(self) -> VaRSnapshot:
        if len(self.returns) < 50:
            se = self.symbolic.evaluate(
                assemble_se41_context(
                    risk_hint=0.3, uncertainty_hint=0.5, coherence_hint=0.5
                )
            )
            return VaRSnapshot(0, 0, 0, 0, 0, 0, 0, 1.0, se, "insufficient")
        arr = list(self.returns)
        losses = sorted([-x for x in arr])  # convert to loss distribution

        def hist_var(p: float) -> float:
            k = int(p * len(losses)) - 1
            k = max(0, min(len(losses) - 1, k))
            return losses[k]

        hv95 = hist_var(0.95)
        hv99 = hist_var(0.99)
        mean = statistics.fmean(arr)
        std = statistics.pstdev(arr)
        para_std = math.sqrt(self.ewma_var) if self.ewma_var else std
        pv95 = -(mean - _Z[0.95] * para_std)
        pv99 = -(mean - _Z[0.99] * para_std)
        # ES (expected shortfall)
        es95_losses = [L for L in losses if L >= hv95]
        es99_losses = [L for L in losses if L >= hv99]
        es95 = sum(es95_losses) / max(1, len(es95_losses))
        es99 = sum(es99_losses) / max(1, len(es99_losses))
        disagreement = abs(pv99 - hv99) / (hv99 + 1e-9)
        # Governance mapping
        risk_hint = _clamp01(0.1 + hv99 * 15)  # scale VaR magnitude
        uncertainty_hint = _clamp01(0.15 + disagreement * 0.7)
        coherence_hint = _clamp01(0.9 - disagreement * 0.8)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={"var": {"hv99": hv99, "pv99": pv99}},
            )
        )
        stability = _clamp01(1 - (se.risk + se.uncertainty) / 2.0)
        explain = f"hv99={hv99:.4f} pv99={pv99:.4f} dis={disagreement:.2f}"
        return VaRSnapshot(
            hv95, hv99, pv95, pv99, es95, es99, disagreement, stability, se, explain
        )

    def snapshot_dict(self) -> Dict[str, Any]:
        s = self.snapshot()
        return {
            "hist_var_95": s.hist_var_95,
            "hist_var_99": s.hist_var_99,
            "para_var_95": s.para_var_95,
            "para_var_99": s.para_var_99,
            "es_95": s.es_95,
            "es_99": s.es_99,
            "disagreement": s.disagreement,
            "stability": s.stability,
            "se41": {
                "risk": s.se41.risk,
                "uncertainty": s.se41.uncertainty,
                "coherence": s.se41.coherence,
            },
            "explain": s.explain,
        }


def _selftest() -> int:  # pragma: no cover
    v = VaREngine()
    v.simulate_random(1000)
    d = v.snapshot_dict()
    assert "hist_var_99" in d
    print("VaREngine selftest", d["hist_var_99"])
    return 0


__all__ = ["VaREngine", "VaRSnapshot"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    v = VaREngine()
    v.simulate_random()
    print(json.dumps(v.snapshot_dict(), indent=2))
