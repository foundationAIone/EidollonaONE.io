"""Hyperparameter Tuner (SE41 Governance-Aware)

What
----
Generic tuner supporting Random Search, Bayesian-like adaptive sampling (simplified),
and Successive Halving style early stopping. Incorporates governance metrics
(risk / uncertainty) to penalize overfit configurations.

Why
---
1. Efficient exploration of strategy or model hyperparameters.
2. Early elimination of weak configs saves compute.
3. Governance gating prevents selection of brittle high-variance configs.
4. Deterministic mode for CI reproducibility.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Callable, Optional, Tuple
import random

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
            class S:
                pass

            s = S()
            s.risk = ctx.get("risk_hint", 0.4)
            s.uncertainty = ctx.get("uncertainty_hint", 0.4)
            s.coherence = ctx.get("coherence_hint", 0.6)
            return s

    def assemble_se41_context(**kw):
        return kw


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class TrialResult:
    config: Dict[str, Any]
    score: float
    adjusted_score: float
    governance: SE41Signals
    steps: int
    stopped_early: bool
    info: Dict[str, Any]


class HyperparameterTuner:
    def __init__(
        self,
        search_space: Dict[str, Tuple[float, float]],
        objective: Callable[[Dict[str, Any], int], Dict[str, Any]],
        symbolic: Optional[SymbolicEquation41] = None,
        seed: int = 42,
    ) -> None:
        self.search_space = search_space
        self.objective = objective  # returns dict with keys: score, risk_hint, uncertainty_hint, coherence_hint, variance(optional)
        self.symbolic = symbolic or SymbolicEquation41()
        random.seed(seed)
        self.history: List[TrialResult] = []

    def _sample_config(self) -> Dict[str, Any]:
        cfg = {}
        for k, (lo, hi) in self.search_space.items():
            cfg[k] = random.uniform(lo, hi)
        return cfg

    def _mutate(self, cfg: Dict[str, Any], scale: float = 0.2) -> Dict[str, Any]:
        new = cfg.copy()
        for k, (lo, hi) in self.search_space.items():
            span = hi - lo
            new[k] = max(lo, min(hi, new[k] + random.uniform(-scale, scale) * span))
        return new

    def _evaluate(
        self, cfg: Dict[str, Any], max_steps: int, early_halving: bool
    ) -> TrialResult:
        best_score = -1e9
        steps = 0
        stopped = False
        info = {}
        for step in range(1, max_steps + 1):
            metrics = self.objective(cfg, step)
            score = metrics["score"]
            if score > best_score:
                best_score = score
                info["best_step"] = step
            steps = step
            if early_halving and step < max_steps and step % (max_steps // 3 or 1) == 0:
                # simple early stop heuristic: if score behind expected frontier
                if score < best_score * 0.6 and step < max_steps * 0.7:
                    stopped = True
                    break
        risk_hint = metrics.get("risk_hint", 0.3)
        uncertainty_hint = metrics.get("uncertainty_hint", 0.3)
        coherence_hint = metrics.get("coherence_hint", 0.6)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
            )
        )
        variance = metrics.get("variance", 0.0)
        penalty = 0.4 * se.risk + 0.3 * se.uncertainty + 0.1 * variance
        adjusted = best_score - penalty + 0.15 * se.coherence
        return TrialResult(cfg, best_score, adjusted, se, steps, stopped, info)

    def random_search(
        self, n: int = 25, max_steps: int = 30, early_halving: bool = True
    ) -> TrialResult:
        best: Optional[TrialResult] = None
        for i in range(n):
            cfg = self._sample_config()
            res = self._evaluate(cfg, max_steps, early_halving)
            self.history.append(res)
            if best is None or res.adjusted_score > best.adjusted_score:
                best = res
        return best  # type: ignore

    def adaptive_search(
        self, n_init: int = 10, n_iter: int = 15, max_steps: int = 40
    ) -> TrialResult:
        # Initial population
        pop: List[TrialResult] = []
        for _ in range(n_init):
            res = self._evaluate(self._sample_config(), max_steps, True)
            self.history.append(res)
            pop.append(res)
        pop.sort(key=lambda r: r.adjusted_score, reverse=True)
        best = pop[0]
        # Adaptive exploitation / exploration
        for _ in range(n_iter):
            parent = random.choice(pop[: max(2, len(pop) // 2)])
            child_cfg = self._mutate(parent.config, scale=0.15)
            res = self._evaluate(child_cfg, max_steps, True)
            self.history.append(res)
            if res.adjusted_score > best.adjusted_score:
                best = res
            pop.append(res)
            pop.sort(key=lambda r: r.adjusted_score, reverse=True)
            pop = pop[:n_init]
        return best

    def best_history(self) -> Optional[TrialResult]:
        return (
            max(self.history, key=lambda r: r.adjusted_score) if self.history else None
        )

    def leaderboard(self, top: int = 5) -> List[Dict[str, Any]]:
        ranked = sorted(self.history, key=lambda r: r.adjusted_score, reverse=True)[
            :top
        ]
        out = []
        for r in ranked:
            out.append(
                {
                    "config": r.config,
                    "score": r.score,
                    "adjusted": r.adjusted_score,
                    "risk": r.governance.risk,
                    "uncertainty": r.governance.uncertainty,
                }
            )
        return out


def _demo_objective(
    cfg: Dict[str, Any], step: int
) -> Dict[str, Any]:  # pragma: no cover
    # Synthetic objective: concave optimum near middle of each range + noise
    base = 0.0
    variance = 0.0
    for k, v in cfg.items():
        base += 1 - (v - 0.5) ** 2 * 4  # parabola peaks at 0.5
    base /= len(cfg)
    noise = random.uniform(-0.05, 0.05)
    score = base + noise * (1 - step / 50)
    variance = abs(noise)
    risk_hint = _clamp01(0.2 + variance * 2)
    uncertainty_hint = _clamp01(0.2 + abs(noise) * 1.5)
    coherence_hint = _clamp01(0.85 - abs(noise) * 0.7)
    return {
        "score": score,
        "risk_hint": risk_hint,
        "uncertainty_hint": uncertainty_hint,
        "coherence_hint": coherence_hint,
        "variance": variance,
    }


def _selftest() -> int:  # pragma: no cover
    space = {"lr": (0.0001, 0.01), "dropout": (0.0, 0.7)}
    tuner = HyperparameterTuner(space, _demo_objective)
    best = tuner.adaptive_search(5, 5)
    print("HyperparameterTuner selftest", best.adjusted_score)
    return 0


__all__ = ["HyperparameterTuner", "TrialResult"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    space = {"param1": (0.0, 1.0), "param2": (0.0, 1.0)}
    t = HyperparameterTuner(space, _demo_objective)
    t.random_search(10)
    print(json.dumps(t.leaderboard(), indent=2))
