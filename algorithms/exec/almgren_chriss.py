"""Simplified Almgren–Chriss style execution schedule."""

from __future__ import annotations

from typing import List


def schedule_shares(total_qty: int, slices: int = 6, risk_aversion: float = 0.5) -> List[int]:
    if slices <= 0:
        raise ValueError("slices must be positive")
    base = total_qty // slices
    weights = [1.0 + risk_aversion * (i / max(1, slices - 1) - 0.5) for i in range(slices)]
    total_weight = sum(weights) or 1.0
    allocation = [max(0, int(round(base * slices * (w / total_weight)))) for w in weights]
    diff = total_qty - sum(allocation)
    index = 0
    while diff != 0 and slices > 0:
        step = 1 if diff > 0 else -1
        allocation[index % slices] = max(0, allocation[index % slices] + step)
        diff -= step
        index += 1
    return allocation
