from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - dev fallback
    def audit(event: str, **payload):  # type: ignore
        return None


def almgren_chriss_path(
    q: float,
    T: float,
    M: int,
    sigma: float,
    lam: float,
    perm: float,
    temp: float,
    v_profile: Sequence[float],
) -> List[Dict[str, Any]]:
    """Simple Almgren–Chriss discrete schedule."""
    qty = float(q)
    horizon = max(1.0, float(T))
    steps = max(1, int(M))
    vol = max(1e-8, float(sigma))
    dt = horizon / steps
    profile = list(v_profile) if v_profile else [1.0 for _ in range(steps)]
    if len(profile) != steps:
        if not profile:
            profile = [1.0 for _ in range(steps)]
        else:
            profile = (profile * (steps // len(profile) + 1))[:steps]
    norm = sum(profile) or 1.0
    target = [qty * (p / norm) for p in profile]
    slices: List[Dict[str, Any]] = []
    remaining = qty
    for idx in range(steps):
        child = target[idx]
        risk_term = lam * vol * math.sqrt(dt)
        impact = perm * remaining + temp * child / max(dt, 1e-6)
        slices.append(
            {
                "t": (idx + 1) * dt,
                "qty": child,
                "remaining": max(0.0, remaining - child),
                "risk_term": risk_term,
                "impact_cost": impact,
                "mode": "AC",
            }
        )
        remaining -= child
    audit(
        "ac_schedule",
        qty=qty,
        horizon=horizon,
        steps=steps,
        lam=float(lam),
        perm=float(perm),
        temp=float(temp),
    )
    return slices


__all__ = ["almgren_chriss_path"]
