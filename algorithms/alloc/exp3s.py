"""Bounded allocation update akin to EXP3.S."""

from __future__ import annotations

from typing import Dict


def bounded_update(weights: Dict[str, float], performance: Dict[str, float], step: float = 0.05) -> Dict[str, float]:
    if not performance:
        return weights
    if not weights:
        base = 1.0 / max(1, len(performance))
        weights = {key: base for key in performance}
    avg = sum(performance.values()) / max(1, len(performance))
    updated = {}
    for key, weight in weights.items():
        delta = step * ((performance.get(key, avg) - avg) / (abs(avg) + 1e-6))
        updated[key] = max(0.0, min(1.0, weight + delta))
    total = sum(updated.values()) or 1.0
    return {key: value / total for key, value in updated.items()}
