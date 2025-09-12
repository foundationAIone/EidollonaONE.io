"""Genetic Strategy Optimizer (SE41)

What
----
Implements a genetic algorithm for optimizing trading / allocation strategy
parameter sets with governance-aware fitness adjustment.

Why
---
1. Population-based exploration avoids local minima.
2. Diversity retention reduces overfit risk (uncertainty gating).
3. Governance metrics modify survivor selection pressure.
4. Deterministic seed path for reproducible CI.
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
class Individual:
    genome: Dict[str, float]
    raw_fitness: float
    adjusted_fitness: float
    governance: SE41Signals


class GeneticOptimizer:
    def __init__(
        self,
        search_space: Dict[str, Tuple[float, float]],
        fitness_fn: Callable[[Dict[str, float]], Dict[str, float]],
        population: int = 30,
        symbolic: Optional[SymbolicEquation41] = None,
        seed: int = 7,
    ) -> None:
        self.space = search_space
        self.fitness_fn = fitness_fn  # returns dict: fitness, risk_hint, uncertainty_hint, coherence_hint
        self.population_size = population
        self.symbolic = symbolic or SymbolicEquation41()
        random.seed(seed)
        self.generation = 0
        self.pop: List[Individual] = []

    def _random_genome(self) -> Dict[str, float]:
        return {k: random.uniform(lo, hi) for k, (lo, hi) in self.space.items()}

    def _mutate(self, g: Dict[str, float], rate: float = 0.2) -> Dict[str, float]:
        ng = g.copy()
        for k, (lo, hi) in self.space.items():
            if random.random() < rate:
                span = hi - lo
                ng[k] = max(lo, min(hi, ng[k] + random.uniform(-0.3, 0.3) * span))
        return ng

    def _crossover(self, a: Dict[str, float], b: Dict[str, float]) -> Dict[str, float]:
        child = {}
        for k in a.keys():
            child[k] = a[k] if random.random() < 0.5 else b[k]
            if random.random() < 0.1:
                lo, hi = self.space[k]
                span = hi - lo
                child[k] = max(lo, min(hi, child[k] + random.uniform(-0.1, 0.1) * span))
        return child

    def _evaluate(self, genome: Dict[str, float]) -> Individual:
        metrics = self.fitness_fn(genome)
        fitness = metrics["fitness"]
        risk = metrics.get("risk_hint", 0.3)
        unc = metrics.get("uncertainty_hint", 0.3)
        coh = metrics.get("coherence_hint", 0.6)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk, uncertainty_hint=unc, coherence_hint=coh
            )
        )
        penalty = 0.5 * se.risk + 0.4 * se.uncertainty
        adjusted = fitness - penalty + 0.25 * se.coherence
        return Individual(genome, fitness, adjusted, se)

    def initialize(self):
        self.pop = [
            self._evaluate(self._random_genome()) for _ in range(self.population_size)
        ]
        self.generation = 0

    def evolve(self, generations: int = 10, elite_fraction: float = 0.2) -> Individual:
        if not self.pop:
            self.initialize()
        elites = max(1, int(self.population_size * elite_fraction))
        best = max(self.pop, key=lambda i: i.adjusted_fitness)
        for _ in range(generations):
            self.pop.sort(key=lambda i: i.adjusted_fitness, reverse=True)
            eliteset = self.pop[:elites]
            offspring: List[Individual] = []
            while len(offspring) < self.population_size - elites:
                p1, p2 = random.sample(eliteset, 2 if len(eliteset) > 1 else 1)
                child_g = self._crossover(
                    p1.genome, p2.genome if len(eliteset) > 1 else p1.genome
                )
                child_g = self._mutate(child_g)
                offspring.append(self._evaluate(child_g))
            self.pop = eliteset + offspring
            self.generation += 1
            gen_best = max(self.pop, key=lambda i: i.adjusted_fitness)
            if gen_best.adjusted_fitness > best.adjusted_fitness:
                best = gen_best
        return best

    def leaderboard(self, top: int = 5) -> List[Dict[str, Any]]:
        self.pop.sort(key=lambda i: i.adjusted_fitness, reverse=True)
        return [
            {
                "fitness": i.raw_fitness,
                "adjusted": i.adjusted_fitness,
                "genome": i.genome,
                "risk": i.governance.risk,
            }
            for i in self.pop[:top]
        ]


def _demo_fitness(genome: Dict[str, float]) -> Dict[str, float]:  # pragma: no cover
    base = 0.0
    for v in genome.values():
        base += 1 - (v - 0.5) ** 2 * 4
    base /= len(genome)
    noise = random.uniform(-0.05, 0.05)
    fitness = base + noise
    risk_hint = _clamp01(0.2 + abs(noise) * 2)
    uncertainty_hint = _clamp01(0.2 + abs(noise) * 1.5)
    coherence_hint = _clamp01(0.85 - abs(noise) * 0.7)
    return {
        "fitness": fitness,
        "risk_hint": risk_hint,
        "uncertainty_hint": uncertainty_hint,
        "coherence_hint": coherence_hint,
    }


def _selftest() -> int:  # pragma: no cover
    space = {"a": (0, 1), "b": (0, 1)}
    go = GeneticOptimizer(space, _demo_fitness, population=12)
    best = go.evolve(3)
    print("GeneticOptimizer selftest", best.adjusted_fitness)
    return 0


__all__ = ["GeneticOptimizer", "Individual"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    space = {"x": (0, 1), "y": (0, 1)}
    go = GeneticOptimizer(space, _demo_fitness)
    go.evolve(5)
    print(json.dumps(go.leaderboard(), indent=2))
