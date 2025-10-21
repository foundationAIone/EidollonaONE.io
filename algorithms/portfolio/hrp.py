"""Box-constrained weight normaliser (HRP placeholder)."""

from __future__ import annotations

from typing import Dict, Iterable


def box_constrained_weights(names: Iterable[str], min_weight: float = 0.05, max_weight: float = 0.40) -> Dict[str, float]:
    names = list(names)
    if not names:
        return {}
    base = 1.0 / len(names)
    weights = {name: base for name in names}
    clipped = {name: max(min_weight, min(max_weight, value)) for name, value in weights.items()}
    total = sum(clipped.values()) or 1.0
    return {name: value / total for name, value in clipped.items()}
