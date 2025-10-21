from __future__ import annotations

from typing import Dict, Literal, Tuple
import math

OptionKind = Literal["call", "put"]

_SQRT2 = math.sqrt(2.0)


def _n(x: float) -> float:
    """Standard normal CDF."""

    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def _phi(x: float) -> float:
    """Standard normal PDF."""

    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


def _clamp_tau(t: float) -> float:
    return max(1e-9, float(t))


def d1_d2(S: float, K: float, r: float, q: float, sigma: float, t: float) -> Tuple[float, float]:
    tau = _clamp_tau(t)
    if sigma <= 0.0 or S <= 0.0 or K <= 0.0:
        return float("nan"), float("nan")
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * tau) / (sigma * math.sqrt(tau))
    d2 = d1 - sigma * math.sqrt(tau)
    return d1, d2


def price(kind: OptionKind, S: float, K: float, r: float, q: float, sigma: float, t: float) -> float:
    """Black–Scholes price with continuous dividend yield ``q``."""

    d1, d2 = d1_d2(S, K, r, q, sigma, t)
    if math.isnan(d1):
        return float("nan")
    tau = _clamp_tau(t)
    df_r = math.exp(-r * tau)
    df_q = math.exp(-q * tau)
    if kind == "call":
        return df_q * S * _n(d1) - df_r * K * _n(d2)
    return df_r * K * _n(-d2) - df_q * S * _n(-d1)


def greeks(kind: OptionKind, S: float, K: float, r: float, q: float, sigma: float, t: float) -> Dict[str, float]:
    """Analytic Greeks for the Black–Scholes model with yield ``q``."""

    d1, d2 = d1_d2(S, K, r, q, sigma, t)
    if math.isnan(d1):
        return {name: float("nan") for name in ("delta", "gamma", "theta", "vega", "rho")}
    tau = _clamp_tau(t)
    st = math.sqrt(tau)
    df_r = math.exp(-r * tau)
    df_q = math.exp(-q * tau)
    pdf = _phi(d1)
    cdf_d1 = _n(d1)
    cdf_d2 = _n(d2)
    delta = df_q * cdf_d1 if kind == "call" else df_q * (cdf_d1 - 1.0)
    gamma = df_q * pdf / (S * sigma * st)
    vega = df_q * S * pdf * st
    theta_common = (-df_q * S * pdf * sigma) / (2.0 * st)
    if kind == "call":
        theta = theta_common - r * df_r * K * cdf_d2 + q * df_q * S * cdf_d1
        rho = K * tau * df_r * cdf_d2
    else:
        theta = theta_common + r * df_r * K * _n(-d2) - q * df_q * S * _n(-d1)
        rho = -K * tau * df_r * _n(-d2)
    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}


def implied_vol(
    kind: OptionKind,
    S: float,
    K: float,
    r: float,
    q: float,
    t: float,
    target_price: float,
    *,
    tol: float = 1e-8,
    max_iter: int = 100,
    bracket: Tuple[float, float] = (1e-6, 5.0),
) -> float:
    """Solve for implied volatility via safeguarded Newton iterations."""

    lo, hi = bracket
    if lo >= hi:
        lo, hi = min(lo, hi), max(lo, hi)
    tau = _clamp_tau(t)
    plo = price(kind, S, K, r, q, lo, tau)
    phi = price(kind, S, K, r, q, hi, tau)
    if math.isnan(plo) or math.isnan(phi):
        return float("nan")
    if target_price < plo:
        return lo
    if target_price > phi:
        return hi

    sigma = 0.5 * (lo + hi)
    for _ in range(max_iter):
        p = price(kind, S, K, r, q, sigma, tau)
        if math.isnan(p):
            return float("nan")
        diff = p - target_price
        if abs(diff) < tol:
            return sigma
        if diff > 0.0:
            hi = sigma
        else:
            lo = sigma
        vega = greeks(kind, S, K, r, q, sigma, tau)["vega"]
        if vega <= 1e-8:
            sigma = 0.5 * (lo + hi)
            continue
        newton = sigma - diff / vega
        if newton <= lo or newton >= hi:
            sigma = 0.5 * (lo + hi)
        else:
            sigma = newton
    return sigma


__all__ = ["price", "greeks", "implied_vol", "d1_d2"]
