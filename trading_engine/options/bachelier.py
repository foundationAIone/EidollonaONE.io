from __future__ import annotations

from typing import Dict, Literal
import math

OptionKind = Literal["call", "put"]

_SQRT2 = math.sqrt(2.0)


def _N(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def _phi(x: float) -> float:
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


def _tau(t: float) -> float:
    return max(1e-9, float(t))


def price(kind: OptionKind, S: float, K: float, r: float, sigma: float, t: float) -> float:
    """Bachelier (normal) model price."""

    tau = _tau(t)
    df = math.exp(-r * tau)
    if sigma <= 0.0:
        intrinsic = max(S - K, 0.0) if kind == "call" else max(K - S, 0.0)
        return df * intrinsic
    denom = sigma * math.sqrt(tau)
    d = (S - K) / denom
    if kind == "call":
        return df * ((S - K) * _N(d) + denom * _phi(d))
    return df * ((K - S) * _N(-d) + denom * _phi(d))


def greeks(kind: OptionKind, S: float, K: float, r: float, sigma: float, t: float) -> Dict[str, float]:
    tau = _tau(t)
    df = math.exp(-r * tau)
    if sigma <= 0.0:
        return {"delta": df if (kind == "call" and S > K) else (-df if kind == "put" and S < K else 0.0),
                "gamma": 0.0,
                "theta": -r * price(kind, S, K, r, sigma, t),
                "vega": 0.0,
                "rho": -t * price(kind, S, K, r, sigma, t)}
    denom = sigma * math.sqrt(tau)
    d = (S - K) / denom
    delta = df * _N(d) if kind == "call" else -df * _N(-d)
    gamma = df * _phi(d) / denom
    vega = df * _phi(d) * math.sqrt(tau)
    theta = -r * price(kind, S, K, r, sigma, t) - df * _phi(d) * sigma / (2.0 * math.sqrt(tau))
    rho = -t * price(kind, S, K, r, sigma, t)
    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}


__all__ = ["price", "greeks", "OptionKind"]
