from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - dev fallback
    def audit(event: str, **payload):  # type: ignore
        return None


def ow_path(
    q: float,
    T: float,
    M: int,
    sigma: float,
    rho: float,
    temp: float,
    v_profile: Sequence[float],
) -> List[Dict[str, Any]]:
    """Obizhaeva–Wang resilience-aware schedule."""
    qty = float(q)
    horizon = max(1.0, float(T))
    steps = max(1, int(M))
    resilience = max(1e-6, float(rho))
    dt = horizon / steps
    profile = list(v_profile) if v_profile else [1.0 for _ in range(steps)]
    if len(profile) != steps:
        profile = (profile * (steps // len(profile) + 1))[:steps]
    norm = sum(profile) or 1.0
    remaining = qty
    slices: List[Dict[str, Any]] = []
    for idx in range(steps):
        frac = profile[idx] / norm
        child = qty * frac
        resilience_factor = math.exp(-resilience * idx * dt)
        impact = temp * child / max(dt, 1e-6)
        slices.append(
            {
                "t": (idx + 1) * dt,
                "qty": child,
                "remaining": max(0.0, remaining - child),
                "resilience": resilience_factor,
                "impact_cost": impact,
                "mode": "OW",
            }
        )
        remaining -= child
    audit(
        "ow_schedule",
        qty=qty,
        horizon=horizon,
        steps=steps,
        rho=resilience,
        temp=float(temp),
    )
    return slices


__all__ = ["ow_path"]
