from __future__ import annotations

from typing import Literal

from trading_engine.options.bsm import greeks as bs_greeks, OptionKind

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

    delta = bs_greeks(kind, S, K, r, q, sigma, t)["delta"]
    return -delta * quantity


__all__ = ["hedge_frequency", "delta_hedge_notional", "Gate", "SovereignGate"]
