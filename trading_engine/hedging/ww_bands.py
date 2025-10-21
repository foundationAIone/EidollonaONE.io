from __future__ import annotations

from typing import Any, Dict

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - development fallback
    def audit(event: str, **payload: Any) -> None:
        return None


_CADENCE = {
    "ROAD": "fast",
    "SHOULDER": "moderate",
    "OFFROAD": "slow",
}


def band_width(
    sigma: float,
    gamma: float,
    costs: Dict[str, float],
    risk_tol: float,
) -> float:
    """Return half-band width under Whalley–Wilmott approximation."""

    sigma = max(1e-6, float(sigma))
    gamma = max(1e-6, float(gamma))
    risk_tol = max(1e-4, float(risk_tol))
    spread_cost = abs(float(costs.get("spread", costs.get("transaction", 0.001))))
    vol_term = sigma ** (2.0 / 3.0)
    cost_term = (3.0 * spread_cost / (2.0 * gamma * risk_tol)) ** (1.0 / 3.0)
    return max(1e-6, vol_term * cost_term)


def next_hedge(
    delta_now: float,
    delta_target: float,
    band: float,
) -> Dict[str, Any]:
    band = max(1e-6, float(band))
    delta_now = float(delta_now)
    delta_target = float(delta_target)
    diff = delta_target - delta_now
    action: str
    size: float
    if abs(diff) <= band:
        action = "HOLD"
        size = 0.0
    else:
        direction = 1.0 if diff > 0 else -1.0
        boundary = delta_target - direction * band * 0.5
        size = boundary - delta_now
        action = "BUY" if size > 0 else "SELL"
    audit(
        "hedge_band_decision",
        action=action,
        size=size,
        delta_now=delta_now,
        delta_target=delta_target,
        band=band,
    )
    return {"action": action, "size": size, "band": band}


def cadence_for_gate(gate: str) -> str:
    return _CADENCE.get(gate.upper(), "moderate")


__all__ = ["band_width", "next_hedge", "cadence_for_gate"]
