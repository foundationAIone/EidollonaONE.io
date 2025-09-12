"""Treasury Surplus Allocation (SE41 Integrated)

What
----
Allocates a provided surplus across strategic internal initiatives
(R&D, Liquidity, Ops, Reserve) using SymbolicEquation41 governance signals
including impetus (innovation drive), risk, uncertainty, coherence and
ethos pillars. Adjusts dynamically for external volatility conditions.

Why
---
1. Ensures surplus deployment aligns with systemic risk posture.
2. Channels momentum / impetus toward innovation when governance stable.
3. Expands protective reserves under elevated risk or uncertainty.
4. Provides transparent explain string for audit + downstream reporting.

Resilience
----------
Falls back to lightweight stub SymbolicEquation41 if symbolic_core is
unavailable so higher-level orchestration / tests still run.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional

try:  # pragma: no cover - dynamic import environment
    from symbolic_core.symbolic_equation import SymbolicEquation41, SE41Signals  # type: ignore
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
except Exception:  # Fallback stub to preserve functionality

    class SE41Signals:  # type: ignore
        def __init__(
            self, risk=0.3, uncertainty=0.3, coherence=0.8, impetus=0.4, ethos=None
        ):
            self.risk = risk
            self.uncertainty = uncertainty
            self.coherence = coherence
            self.impetus = impetus
            self.ethos = ethos or {}

    class SymbolicEquation41:  # type: ignore
        def evaluate(self, ctx):
            # Return deterministic mid-ground signals from hints
            risk = ctx.get("risk_hint", 0.3)
            unc = ctx.get("uncertainty_hint", 0.3)
            coh = ctx.get("coherence_hint", 0.8)
            impetus = 0.4 + 0.3 * (coh - (risk + unc) / 2)
            ethos = {
                "authenticity": 0.9,
                "integrity": 0.85,
                "responsibility": 0.92,
                "enrichment": 0.88,
            }
            return SE41Signals(risk, unc, coh, impetus, ethos)

    def assemble_se41_context(**kw):
        return kw


INITIATIVES = ["R&D", "Liquidity", "Ops", "Reserve"]


@dataclass
class AllocationPlan:
    total: float
    weights: Dict[str, float]
    se41: SE41Signals
    explain: str


class TreasuryAllocator:
    def __init__(self, symbolic: Optional[SymbolicEquation41] = None) -> None:
        self.symbolic = symbolic or SymbolicEquation41()

    def allocate(self, total: float, volatility_index: float = 0.15) -> AllocationPlan:
        # Map external volatility to risk/uncertainty; impetus drives R&D share
        v = max(0.0, min(1.0, volatility_index))
        risk_hint = 0.12 + v * 0.5
        uncertainty_hint = 0.25 + v * 0.4
        coherence_hint = 0.82 - v * 0.2
        ctx = assemble_se41_context(
            coherence_hint=coherence_hint,
            risk_hint=risk_hint,
            uncertainty_hint=uncertainty_hint,
            extras={"treasury": {"volatility_index": v}},
        )
        se = self.symbolic.evaluate(ctx)

        # Base weights seeded by ethos pillars (authenticity->R&D, integrity->Ops, responsibility->Reserve, enrichment->Liquidity)
        ethos = se.ethos
        base = {
            "R&D": ethos.get("authenticity", 0.9),
            "Ops": ethos.get("integrity", 0.9),
            "Reserve": ethos.get("responsibility", 0.9),
            "Liquidity": ethos.get("enrichment", 0.9),
        }
        # Adjust: higher risk shifts weight to Reserve, higher impetus shifts to R&D
        reserve_shift = se.risk * 0.6
        rnd_shift = se.impetus * 0.5
        base["Reserve"] += reserve_shift
        base["R&D"] += rnd_shift
        # Normalize
        total_base = sum(base.values()) or 1.0
        weights = {k: v / total_base for k, v in base.items()}
        plan = {k: round(total * w, 2) for k, w in weights.items()}
        explain = (
            f"vol={v:.2f} risk={se.risk:.2f} unc={se.uncertainty:.2f} coh={se.coherence:.2f} "
            f"impetus={se.impetus:.2f} reserve_shift={reserve_shift:.2f} rnd_shift={rnd_shift:.2f}"
        )
        return AllocationPlan(total=total, weights=plan, se41=se, explain=explain)


__all__ = ["TreasuryAllocator", "AllocationPlan"]
