from __future__ import annotations

import math
from typing import Any, Dict

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - development fallback
    def audit(event: str, **payload: Any) -> None:
        return None


def optimal_spread(
    inventory: float,
    sigma: float,
    kappa: float,
    horizon: float,
    risk_aversion: float,
) -> Dict[str, float]:
    """Compute Avellaneda–Stoikov optimal bid/ask half-spreads."""

    sigma = max(1e-6, float(sigma))
    kappa = max(1e-6, float(kappa))
    horizon = max(1e-6, float(horizon))
    gamma = max(1e-6, float(risk_aversion))
    inventory = float(inventory)

    base = gamma * sigma * sigma * horizon
    adjustment = (2.0 / kappa) * math.log1p(kappa / gamma)
    half_spread = 0.5 * (base + adjustment)
    inv_term = inventory * gamma * sigma * sigma * horizon * 0.5
    bid_half = max(1e-6, half_spread + inv_term)
    ask_half = max(1e-6, half_spread - inv_term)
    return {"bid": bid_half, "ask": ask_half}


def reservation_price(mid: float, inventory: float, gamma: float, sigma: float, horizon: float = 1.0) -> float:
    mid = float(mid)
    gamma = max(1e-6, float(gamma))
    sigma = max(1e-6, float(sigma))
    horizon = max(1e-6, float(horizon))
    inventory = float(inventory)
    return mid - inventory * gamma * sigma * sigma * horizon


def passive_quote(
    mid: float,
    inventory: float,
    sigma: float,
    kappa: float,
    horizon: float,
    risk_aversion: float,
) -> Dict[str, Any]:
    spreads = optimal_spread(inventory, sigma, kappa, horizon, risk_aversion)
    r_star = reservation_price(mid, inventory, risk_aversion, sigma, horizon)
    bid = max(0.0, r_star - spreads["bid"])
    ask = max(bid, r_star + spreads["ask"])
    quote = {
        "bid": bid,
        "ask": ask,
        "reservation": r_star,
        "inventory": inventory,
        "spreads": spreads,
    }
    audit(
        "as_quote",
        mid=mid,
        bid=bid,
        ask=ask,
        reservation=r_star,
        inventory=inventory,
    )
    return quote


__all__ = ["optimal_spread", "reservation_price", "passive_quote"]
