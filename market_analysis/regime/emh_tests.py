from __future__ import annotations

from typing import Dict, List
import math


def runs_test(returns: List[float]) -> Dict[str, float]:
    """Runs test for randomness using median sign splits."""

    if not returns:
        return {"z": 0.0, "p_approx": 1.0}
    sorted_vals = sorted(returns)
    median = sorted_vals[len(sorted_vals) // 2]
    signs = [1 if x >= median else -1 for x in returns]
    n1 = sum(1 for s in signs if s == 1)
    n2 = len(signs) - n1
    runs = 1 + sum(1 for i in range(1, len(signs)) if signs[i] != signs[i - 1])
    denom = n1 + n2
    mu = 1.0 + (2.0 * n1 * n2) / denom if denom > 0 else 0.0
    var = (
        (2.0 * n1 * n2 * (2.0 * n1 * n2 - denom)) / (denom * denom * (denom - 1))
        if denom > 1
        else 1.0
    )
    z = (runs - mu) / math.sqrt(var) if var > 0.0 else 0.0
    p = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))
    return {"z": z, "p_approx": p}


__all__ = ["runs_test"]
