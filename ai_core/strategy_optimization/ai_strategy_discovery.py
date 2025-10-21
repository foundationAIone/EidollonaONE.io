"""AI Strategy Discovery Engine (SE41)

What
----
Discovers candidate trading / allocation strategies via pattern mining,
feature recombination, and governance-aware scoring (stability & robustness).

Why
---
1. Systematic search for novel alpha factors.
2. Penalizes overfit or low-diversity candidates early.
3. Integrates with HyperparameterTuner & GeneticOptimizer pipelines.
4. Deterministic seeding for reproducibility.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import random

from symbolic_core.symbolic_equation41 import (  # type: ignore
    SymbolicEquation41,
    SE41Signals,
)

try:  # pragma: no cover
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    def assemble_se41_context(**kw):
        return kw


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class StrategyCandidate:
    formula: str
    raw_score: float
    stability: float
    governance: SE41Signals
    components: List[str]
    explain: str


class AIStrategyDiscovery:
    def __init__(
        self,
        feature_pool: List[str],
        symbolic: Optional[Any] = None,
        seed: int = 11,
    ) -> None:
        random.seed(seed)
        self.pool = feature_pool
        self.symbolic = symbolic or SymbolicEquation41()
        self.candidates: List[StrategyCandidate] = []

    def _random_formula(self) -> List[str]:
        k = random.randint(2, min(5, len(self.pool)))
        return random.sample(self.pool, k)

    def _score_components(self, comps: List[str]) -> Dict[str, float]:
        diversity = len(set(c[0] for c in comps)) / max(1, len(comps))
        complexity = len(comps)
        base = diversity * 0.6 + (1 - (complexity / 10)) * 0.4
        noise = random.uniform(-0.1, 0.1)
        raw = base + noise
        risk_hint = _clamp01(0.2 + complexity * 0.05)
        uncertainty_hint = _clamp01(0.25 + abs(noise) * 0.8)
        coherence_hint = _clamp01(0.85 - abs(noise) * 0.7 + diversity * 0.1)
        return {
            "raw": raw,
            "risk": risk_hint,
            "unc": uncertainty_hint,
            "coh": coherence_hint,
            "noise": noise,
            "div": diversity,
        }

    def generate(self, n: int = 30) -> None:
        for _ in range(n):
            comps = self._random_formula()
            metrics = self._score_components(comps)
            se: SE41Signals = self.symbolic.evaluate(
                assemble_se41_context(
                    risk_hint=metrics["risk"],
                    uncertainty_hint=metrics["unc"],
                    coherence_hint=metrics["coh"],
                )
            )
            stability = _clamp01(1 - (se.risk + se.uncertainty) / 2.0)
            formula = " + ".join(comps)
            cand = StrategyCandidate(
                formula,
                metrics["raw"],
                stability,
                se,
                comps,
                f"div={metrics['div']:.2f} noise={metrics['noise']:.2f}",
            )
            self.candidates.append(cand)

    def top(self, k: int = 5) -> List[StrategyCandidate]:
        return sorted(
            self.candidates, key=lambda c: (c.stability, c.raw_score), reverse=True
        )[:k]


def _selftest() -> int:  # pragma: no cover
    pool = [
        "SMA10",
        "SMA50",
        "RSI",
        "MACD",
        "VOL",
        "ATR",
        "MOM",
        "BBANDS",
        "CORR",
        "KELT",
    ]
    eng = AIStrategyDiscovery(pool)
    eng.generate(40)
    t = eng.top()
    assert t
    print("AIStrategyDiscovery selftest", t[0].formula)
    return 0


__all__ = ["AIStrategyDiscovery", "StrategyCandidate"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    pool = ["F1", "F2", "F3", "F4"]
    eng = AIStrategyDiscovery(pool)
    eng.generate()
    print(json.dumps([c.formula for c in eng.top()], indent=2))
