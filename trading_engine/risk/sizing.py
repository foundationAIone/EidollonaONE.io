from __future__ import annotations

import math
from typing import Iterable, List

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - dev fallback
    def audit(event: str, **payload):  # type: ignore
        return None


def fractional_kelly(mu: float, sigma: float, cap: float = 0.5) -> float:
    """Return a bounded fractional Kelly weight.

    Args:
        mu: expected excess return per unit capital.
        sigma: volatility of returns (standard deviation).
        cap: absolute cap for the Kelly fraction.
    """
    if sigma <= 0:
        return 0.0
    full_kelly = mu / max(1e-9, sigma * sigma)
    frac = max(-cap, min(cap, full_kelly))
    audit("risk_fractional_kelly", mu=float(mu), sigma=float(sigma), weight=frac)
    return frac


def drawdown_penalty(equity_curve: Iterable[float], alpha: float = 0.5) -> float:
    """Return a penalty factor in [0, 1] based on max drawdown."""
    peak = -math.inf
    max_dd = 0.0
    for value in equity_curve:
        v = float(value)
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
        else:
            dd = 0.0
        if dd > max_dd:
            max_dd = dd
    penalty = max(0.0, 1.0 - alpha * max_dd)
    audit("risk_drawdown_penalty", drawdown=max_dd, penalty=penalty)
    return penalty


def risk_parity(weights: Iterable[float], vols: Iterable[float]) -> List[float]:
    """Compute naive risk parity weights proportional to 1/vol."""
    inverse = []
    for w, vol in zip(weights, vols):
        sigma = abs(float(vol))
        if sigma <= 0:
            inverse.append(0.0)
        else:
            inverse.append(abs(float(w)) / sigma)
    total = sum(inverse)
    if total <= 0:
        return [0.0 for _ in inverse]
    parity = [val / total for val in inverse]
    audit("risk_parity", weights=list(weights), vols=list(vols), parity=parity)
    return parity


__all__ = ["fractional_kelly", "drawdown_penalty", "risk_parity"]
