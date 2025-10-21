"""Metrics helpers for probability assimilation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping

__all__ = ["AssimilationMetrics"]


@dataclass
class AssimilationMetrics:
    """Capture basic statistics during assimilation runs."""

    observations: int = 0
    total_mass: float = 0.0
    last_distribution: Dict[str, float] = field(default_factory=dict)

    def observe_distribution(self, distribution: Mapping[str, float], *, total: float) -> None:
        self.observations += 1
        self.total_mass += float(total)
        self.last_distribution = {str(k): float(v) for k, v in distribution.items()}

    def finalize(self, merged: Mapping[str, float]) -> None:
        self.last_distribution = {str(k): float(v) for k, v in merged.items()}

    def summary(self) -> Dict[str, float]:
        average_mass = self.total_mass / max(1, self.observations)
        return {
            "observations": float(self.observations),
            "average_mass": float(average_mass),
        }
