"""Shared helpers for SAFE Qiskit compatibility layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, MutableMapping

__all__ = ["AlgorithmResult", "ProbabilityHistogram", "clamp_probability", "normalize_histogram"]


@dataclass
class AlgorithmResult:
    """Simple result container mimicking Qiskit's algorithm outputs."""

    value: float
    metadata: Mapping[str, Any]
    error: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            "value": float(self.value),
            "metadata": dict(self.metadata),
            "error": float(self.error),
        }


ProbabilityHistogram = Mapping[str, float]


def clamp_probability(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_histogram(histogram: Mapping[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, float(val)) for val in histogram.values())
    if total <= 0.0:
        count = max(1, len(histogram))
        normalized = {str(idx): 1.0 / count for idx in range(count)}
    else:
        normalized = {key: max(0.0, float(val)) / total for key, val in histogram.items()}
    if isinstance(histogram, MutableMapping):
        histogram.clear()
        histogram.update(normalized)
    return normalized
