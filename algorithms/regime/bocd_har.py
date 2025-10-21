"""Minimal regime classifier placeholder."""

from __future__ import annotations


def regime_flag(realized_vol: float, threshold: float = 1.5) -> str:
    if realized_vol > threshold:
        return "stress"
    if realized_vol > 1.0:
        return "trend"
    return "chop"
