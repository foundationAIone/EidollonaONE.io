# ======================================================================
# 📐 EidollonaONE Greeks Calculator (Black–Scholes & Black‑76) v4.1+
# SE41-aligned option Greeks with robust numerics and higher-order set.
#
# References:
# - Black–Scholes model overview & Greeks: Wikipedia “Black–Scholes model”.
# - General definitions & higher-order Greeks: Wikipedia “Greeks (finance)”.
#   (Formulas for Δ, Γ, ϑ, ρ, ν; and Vanna, Vomma/Volga, Charm, Speed, Color,
#    Zomma, Veta, Ultima, as commonly given in closed form.)
# ======================================================================
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import exp, log, sqrt, erf, pi
from typing import Dict, Optional, Literal

# --- Optional SE41 alignment -------------------------------------------------
try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41  # noqa: F401
    from symbolic_core.se41_context import assemble_se41_context  # noqa: F401
    from trading.helpers.se41_trading_gate import se41_numeric  # noqa: F401

    _SE41 = True
except Exception:  # pragma: no cover
    _SE41 = False

    def se41_numeric(**_kw):  # type: ignore
        return 0.73


CallPut = Literal["call", "put"]


# --- Normal pdf/cdf with stable numerics ------------------------------------
SQRT_2PI = sqrt(2.0 * pi)


def _phi(x: float) -> float:
    return exp(-0.5 * x * x) / SQRT_2PI


def _Phi(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


# --- Utility: d1, d2 with guardrails ----------------------------------------
def _d1_d2(
    S: float, K: float, T: float, r: float, q: float, sigma: float
) -> tuple[float, float]:
    eps_T = max(T, 1e-16)
    eps_sig = max(sigma, 1e-16)
    vsqrt = eps_sig * sqrt(eps_T)
    mu = (r - q + 0.5 * eps_sig * eps_sig) * eps_T
    x = log(max(S, 1e-300) / max(K, 1e-300))
    d1 = (x + mu) / vsqrt
    d2 = d1 - vsqrt
    return d1, d2


def _d1_d2_black76(F: float, K: float, T: float, sigma: float) -> tuple[float, float]:
    eps_T = max(T, 1e-16)
    eps_sig = max(sigma, 1e-16)
    vsqrt = eps_sig * sqrt(eps_T)
    x = log(max(F, 1e-300) / max(K, 1e-300))
    d1 = (x + 0.5 * eps_sig * eps_sig * eps_T) / vsqrt
    d2 = d1 - vsqrt
    return d1, d2


# --- Dataclass for a comprehensive Greeks bundle -----------------------------
@dataclass
class Greeks:
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    vanna: float
    vomma: float
    charm: float
    speed: float
    color: float
    zomma: float
    veta: float
    ultima: float
    vega_per_1pct: float
    theta_per_day: float
    se41_coherence: Optional[float] = None

    def as_dict(self) -> Dict[str, float]:
        return asdict(self)


# --- Black–Scholes Greeks (spot/dividend) ------------------------------------
def greeks_black_scholes(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    kind: CallPut = "call",
    *,
    compute_higher: bool = True,
    days_in_year: float = 365.0,
    se41: bool = True,
) -> Greeks:
    d1, d2 = _d1_d2(S, K, T, r, q, sigma)
    Nd1, Nd2 = _Phi(d1), _Phi(d2)
    Nmd1, Nmd2 = _Phi(-d1), _Phi(-d2)
    phid1 = _phi(d1)
    df_q = exp(-q * max(T, 0.0))
    df_r = exp(-r * max(T, 0.0))
    sqrtT = sqrt(max(T, 1e-16))
    denom = max(S * max(sigma, 1e-16) * sqrtT, 1e-300)

    if kind == "call":
        delta = df_q * Nd1
        theta = (
            -(S * df_q * phid1 * sigma) / (2.0 * sqrtT)
            - r * K * df_r * Nd2
            + q * S * df_q * Nd1
        )
        rho = K * T * df_r * Nd2
    else:
        delta = -df_q * Nmd1
        theta = (
            -(S * df_q * phid1 * sigma) / (2.0 * sqrtT)
            + r * K * df_r * Nmd2
            - q * S * df_q * Nmd1
        )
        rho = -K * T * df_r * Nmd2

    gamma = df_q * phid1 / denom
    vega = S * df_q * phid1 * sqrtT

    if compute_higher:
        vanna = df_q * phid1 * (-(d2) / max(sigma, 1e-16))
        vomma = vega * (d1 * d2) / max(sigma, 1e-16)
        sign = +1.0 if kind == "call" else -1.0
        charm = sign * q * df_q * (Nd1 if kind == "call" else Nmd1) - df_q * phid1 * (
            2.0 * (r - q) * max(T, 1e-16) - d2 * max(sigma, 1e-16) * sqrtT
        ) / (2.0 * max(T, 1e-16) * max(sigma, 1e-16) * sqrtT)
        speed = -gamma / max(S, 1e-300) * (1.0 + d1 / max(sigma * sqrtT, 1e-16))
        color = (
            -(df_q * phid1)
            / (2.0 * max(S, 1e-300) * max(T, 1e-16) * max(sigma * sqrtT, 1e-16))
            * (2.0 * q * max(T, 1e-16) + 1.0 + d1 * d2)
        )
        zomma = gamma * ((d1 * d2 - 1.0) / max(sigma, 1e-16))
        veta = -S * df_q * phid1 * sqrtT * (q + (d1 * d2) / (2.0 * max(T, 1e-16)))
        sig2 = max(sigma, 1e-16) ** 2
        ultima = -vega * (d1 * d2 * (1.0 - d1 * d2) + d1 * d1 + d2 * d2) / sig2
    else:
        vanna = vomma = charm = speed = color = zomma = veta = ultima = 0.0

    vega_per_1pct = vega / 100.0
    theta_per_day = theta / days_in_year

    coherence = None
    if se41:
        try:
            DNA = [
                1.0,
                min(abs(delta), 1.0),
                min(abs(gamma) * S, 5.0) / 5.0,
                min(abs(vega) / max(S, 1e-8), 5.0) / 5.0,
                1.1,
            ]
            HP = [1.0, 1.2, min(abs(d1), 6.0) / 6.0, min(abs(d2), 6.0) / 6.0, 1.3]
            raw = se41_numeric(M_t=0.6, DNA_states=DNA, harmonic_patterns=HP)
            coherence = max(
                0.0,
                min((abs(raw) if isinstance(raw, (float, int)) else 0.7) / 1.2, 1.0),
            )
        except Exception:
            coherence = None

    return Greeks(
        delta,
        gamma,
        vega,
        theta,
        rho,
        vanna,
        vomma,
        charm,
        speed,
        color,
        zomma,
        veta,
        ultima,
        vega_per_1pct,
        theta_per_day,
        coherence,
    )


# --- Black‑76 Greeks (forward/futures) ---------------------------------------
def greeks_black76(
    F: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    kind: CallPut = "call",
    *,
    compute_higher: bool = True,
    days_in_year: float = 365.0,
    se41: bool = True,
) -> Greeks:
    d1, d2 = _d1_d2_black76(F, K, T, sigma)
    Nd1, Nd2 = _Phi(d1), _Phi(d2)
    Nmd1, Nmd2 = _Phi(-d1), _Phi(-d2)
    phid1 = _phi(d1)
    df_r = exp(-r * max(T, 0.0))
    sqrtT = sqrt(max(T, 1e-16))
    denom = max(F * max(sigma, 1e-16) * sqrtT, 1e-300)

    if kind == "call":
        delta = df_r * Nd1
        theta = -(df_r * F * phid1 * sigma) / (2.0 * sqrtT) - r * df_r * (
            F * Nd1 - K * Nd2
        )
        rho = T * df_r * (K * Nd2 - F * Nd1)
    else:
        delta = -df_r * Nmd1
        theta = -(df_r * F * phid1 * sigma) / (2.0 * sqrtT) - r * df_r * (
            K * Nmd2 - F * Nmd1
        )
        rho = T * df_r * (F * Nmd1 - K * Nmd2)

    gamma = df_r * phid1 / denom
    vega = df_r * F * phid1 * sqrtT

    if compute_higher:
        vanna = df_r * phid1 * (-(d2) / max(sigma, 1e-16))
        vomma = vega * (d1 * d2) / max(sigma, 1e-16)
        charm = (
            -df_r
            * phid1
            * (2.0 * (r - 0.0) * max(T, 1e-16) - d2 * max(sigma, 1e-16) * sqrtT)
            / (2.0 * max(T, 1e-16) * max(sigma, 1e-16) * sqrtT)
        )
        speed = -gamma / max(F, 1e-300) * (1.0 + d1 / max(sigma * sqrtT, 1e-16))
        color = (
            -(df_r * phid1)
            / (2.0 * max(F, 1e-300) * max(T, 1e-16) * max(sigma * sqrtT, 1e-16))
            * (1.0 + d1 * d2)
        )
        zomma = gamma * ((d1 * d2 - 1.0) / max(sigma, 1e-16))
        veta = -df_r * F * phid1 * sqrtT * ((d1 * d2) / (2.0 * max(T, 1e-16)))
        sig2 = max(sigma, 1e-16) ** 2
        ultima = -vega * (d1 * d2 * (1.0 - d1 * d2) + d1 * d1 + d2 * d2) / sig2
    else:
        vanna = vomma = charm = speed = color = zomma = veta = ultima = 0.0

    vega_per_1pct = vega / 100.0
    theta_per_day = theta / days_in_year

    coherence = None
    if se41:
        try:
            DNA = [
                1.0,
                min(abs(delta), 1.0),
                min(abs(gamma) * F, 5.0) / 5.0,
                min(abs(vega) / max(F, 1e-8), 5.0) / 5.0,
                1.1,
            ]
            HP = [1.0, 1.2, min(abs(d1), 6.0) / 6.0, min(abs(d2), 6.0) / 6.0, 1.3]
            raw = se41_numeric(M_t=0.6, DNA_states=DNA, harmonic_patterns=HP)
            coherence = max(
                0.0,
                min((abs(raw) if isinstance(raw, (float, int)) else 0.7) / 1.2, 1.0),
            )
        except Exception:
            coherence = None

    return Greeks(
        delta,
        gamma,
        vega,
        theta,
        rho,
        vanna,
        vomma,
        charm,
        speed,
        color,
        zomma,
        veta,
        ultima,
        vega_per_1pct,
        theta_per_day,
        coherence,
    )


# --- Finite-difference validator (BSM) ---------------------------------------
def finite_diff_greeks_bsm(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    kind: CallPut = "call",
    bump_S: float = 1e-3,
    bump_sig: float = 1e-4,
    bump_T: float = 1e-4,
    bump_r: float = 1e-5,
) -> Dict[str, float]:
    def price_bsm(spot: float, vol: float, tau: float, rate: float) -> float:
        d1, d2 = _d1_d2(spot, K, tau, rate, q, vol)
        df_q = exp(-q * tau)
        df_r = exp(-rate * tau)
        if kind == "call":
            return spot * df_q * _Phi(d1) - K * df_r * _Phi(d2)
        return K * df_r * _Phi(-d2) - spot * df_q * _Phi(-d1)

    vp = price_bsm(S + bump_S, sigma, T, r)
    vm = price_bsm(S - bump_S, sigma, T, r)
    delta = (vp - vm) / (2.0 * bump_S)
    vpp = price_bsm(S + bump_S, sigma, T, r)
    v0 = price_bsm(S, sigma, T, r)
    vmm = price_bsm(S - bump_S, sigma, T, r)
    gamma = (vpp - 2.0 * v0 + vmm) / (bump_S * bump_S)
    vega = (
        price_bsm(S, sigma + bump_sig, T, r) - price_bsm(S, sigma - bump_sig, T, r)
    ) / (2.0 * bump_sig)
    theta = (
        price_bsm(S, sigma, T + bump_T, r) - price_bsm(S, sigma, T - bump_T, r)
    ) / (2.0 * bump_T)
    rho = (price_bsm(S, sigma, T, r + bump_r) - price_bsm(S, sigma, T, r - bump_r)) / (
        2.0 * bump_r
    )
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "rho": rho}


__all__ = [
    "Greeks",
    "greeks_black_scholes",
    "greeks_black76",
    "finite_diff_greeks_bsm",
]


if __name__ == "__main__":  # pragma: no cover
    S, K, T, r, q, sigma = 100.0, 100.0, 0.5, 0.03, 0.01, 0.25
    g_call = greeks_black_scholes(S, K, T, r, sigma, q, kind="call")
    g_put = greeks_black_scholes(S, K, T, r, sigma, q, kind="put")
    print("== Black–Scholes (with q) Greeks ==")
    print("Call:", g_call.as_dict())
    print("Put :", g_put.as_dict())
    F, K2, T2, r2, sig2 = 102.0, 100.0, 0.75, 0.025, 0.22
    g_b76 = greeks_black76(F, K2, T2, r2, sig2, kind="call")
    print("\n== Black‑76 Greeks (forward/futures) ==")
    print("Call on futures:", g_b76.as_dict())
