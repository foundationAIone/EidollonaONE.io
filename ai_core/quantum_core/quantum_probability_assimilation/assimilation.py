"""SAFE-friendly probability assimilation routines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping

from .metrics import AssimilationMetrics

__all__ = ["ProbabilityAssimilator", "assimilate_probabilities"]


@dataclass
class ProbabilityAssimilator:
    """Blend multiple probability distributions in a deterministic manner."""

    metrics: AssimilationMetrics = field(default_factory=AssimilationMetrics)

    def assimilate(self, distributions: Iterable[Mapping[str, float]]) -> Dict[str, float]:
        combined: Dict[str, float] = {}
        for dist in distributions:
            total = sum(max(0.0, float(val)) for val in dist.values()) or 1.0
            self.metrics.observe_distribution(dist, total=total)
            for key, value in dist.items():
                combined[key] = combined.get(key, 0.0) + max(0.0, float(value))
        grand_total = sum(combined.values()) or 1.0
        normalized = {key: value / grand_total for key, value in combined.items()}
        self.metrics.finalize(normalized)
        return normalized


def assimilate_probabilities(*distributions: Mapping[str, float]) -> Dict[str, float]:
    return ProbabilityAssimilator().assimilate(distributions)
