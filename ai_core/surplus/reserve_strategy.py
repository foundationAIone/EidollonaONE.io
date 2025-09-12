"""Reserve Strategy Allocator (SE41)

What
----
Allocates total reserve amount into sub-buckets: Emergency, Strategic,
Stability, Opportunistic based on governance risk posture & impetus.

Why
---
1. Granular reserve composition improves transparency.
2. Increases Emergency/Stability share as risk & uncertainty rise.
3. Expands Strategic/Opportunistic share when coherence & impetus strong.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional

try:  # pragma: no cover
    from symbolic_core.symbolic_equation import SymbolicEquation41, SE41Signals  # type: ignore
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
except Exception:  # fallback

    class SE41Signals:  # type: ignore
        def __init__(self, risk=0.3, uncertainty=0.3, coherence=0.8, impetus=0.4):
            self.risk = risk
            self.uncertainty = uncertainty
            self.coherence = coherence
            self.impetus = impetus

    class SymbolicEquation41:  # type: ignore
        def evaluate(self, ctx):
            risk = ctx.get("risk_hint", 0.3)
            unc = ctx.get("uncertainty_hint", 0.3)
            coh = ctx.get("coherence_hint", 0.8)
            imp = 0.4 + (coh - (risk + unc) / 2) * 0.3
            return SE41Signals(risk, unc, coh, imp)

    def assemble_se41_context(**kw):
        return kw


BUCKETS = ["Emergency", "Stability", "Strategic", "Opportunistic"]


@dataclass
class ReserveAllocation:
    total: float
    buckets: Dict[str, float]
    se41: SE41Signals
    explain: str


class ReserveStrategyAllocator:
    def __init__(self, symbolic: Optional[SymbolicEquation41] = None) -> None:
        self.symbolic = symbolic or SymbolicEquation41()

    def allocate(self, total: float, market_stress: float = 0.2) -> ReserveAllocation:
        s = max(0.0, min(1.0, market_stress))
        risk_hint = 0.18 + s * 0.6
        uncertainty_hint = 0.22 + s * 0.55
        coherence_hint = 0.84 - s * 0.25
        ctx = assemble_se41_context(
            risk_hint=risk_hint,
            uncertainty_hint=uncertainty_hint,
            coherence_hint=coherence_hint,
        )
        se = self.symbolic.evaluate(ctx)
        base = {
            "Emergency": 0.25 + se.risk * 0.5 + se.uncertainty * 0.2,
            "Stability": 0.25 + se.risk * 0.3 + se.uncertainty * 0.3,
            "Strategic": 0.25 + se.coherence * 0.25 + se.impetus * 0.25 - se.risk * 0.2,
            "Opportunistic": 0.25
            + se.impetus * 0.4
            + se.coherence * 0.15
            - se.uncertainty * 0.25,
        }
        total_w = sum(base.values()) or 1.0
        alloc = {k: round(total * v / total_w, 2) for k, v in base.items()}
        explain = f"stress={s:.2f} risk={se.risk:.2f} unc={se.uncertainty:.2f} coh={se.coherence:.2f} impetus={getattr(se,'impetus',0.4):.2f}"  # type: ignore
        return ReserveAllocation(total, alloc, se, explain)


__all__ = ["ReserveStrategyAllocator", "ReserveAllocation"]


def _selftest() -> int:  # pragma: no cover
    r = ReserveStrategyAllocator()
    a = r.allocate(1000, 0.3)
    assert abs(sum(a.buckets.values()) - 1000) < 1
    print("ReserveStrategyAllocator selftest", a.explain)
    return 0


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(_selftest())
