from __future__ import annotations

from typing import Literal

from black_scholes.black_scholes_model import OptionKind, greeks, price

Gate = Literal["ALLOW", "REVIEW", "HOLD"]
SovereignGate = Literal["ROAD", "SHOULDER", "OFFROAD"]


def hedge_frequency(sovereign_gate: SovereignGate, gate: Gate) -> float:
    """Return minutes between re-hedges based on gate posture."""

    if gate == "HOLD" or sovereign_gate == "OFFROAD":
        return 60.0
    if gate == "REVIEW" or sovereign_gate == "SHOULDER":
        return 20.0
    return 3.0


def delta_hedge_notional(
    kind: OptionKind,
    S: float,
    K: float,
    r: float,
    q: float,
    sigma: float,
    t: float,
    quantity: float,
) -> float:
    """Compute hedge shares for delta-neutral stance (short option perspective)."""

    delta = greeks(kind, S, K, r, q, sigma, t)["delta"]
    return -delta * quantity


def option_mark_to_market(
    kind: OptionKind,
    S: float,
    K: float,
    r: float,
    q: float,
    sigma: float,
    t: float,
    quantity: float,
) -> float:
    """Mark-to-market value of the option position."""

    px = price(kind, S, K, r, q, sigma, t)
    return px * quantity


__all__ = [
    "hedge_frequency",
    "delta_hedge_notional",
    "option_mark_to_market",
]
