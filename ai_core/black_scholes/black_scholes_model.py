"""
📈 Black–Scholes (BSM) & Black ’76 (B76) – SE41‑aligned model utilities.

Features
- BSM (spot, continuous dividend yield q) call/put prices + full Greeks
- Black ’76 (forward/futures) call/put prices + key Greeks (w.r.t. F)
- Implied volatility via robust bisection (monotone in σ for Euro calls/puts)
- Edge‑safe handling (T=0, σ=0, deep ITM/OTM, numerical stability)
- Put–call parity checks and parity residuals
- Optional SE41 symbolic "coherence" score for diagnostics

Conventions
- S: spot price, K: strike, F: forward/futures, r: risk‑free rate (cont. comp.)
- q: continuous dividend (or convenience yield); T in years; σ in annual vol units
- All outputs are floats; Greeks follow standard risk (spot) conventions for BSM.
- Greeks under Black ’76 are w.r.t. the forward F unless otherwise noted.

Self‑contained, no external dependencies.
"""

from __future__ import annotations

# ───────────────────────────────────────────────────────────────────────────────
# Unified SE41 import & helper stanza (graceful fallbacks if not installed)
# ───────────────────────────────────────────────────────────────────────────────
try:  # pragma: no cover - optional dependency
    from trading.helpers.se41_trading_gate import se41_numeric, ethos_decision  # type: ignore

    _SE41_AVAILABLE = True
except Exception:  # pragma: no cover
    _SE41_AVAILABLE = False

    def se41_numeric(**_kw):  # type: ignore
        return {"score": 0.66}

    def ethos_decision(_tx):  # type: ignore
        return {"decision": "allow"}


# ───────────────────────────────────────────────────────────────────────────────
# Standard library
# ───────────────────────────────────────────────────────────────────────────────
from dataclasses import dataclass
from typing import Tuple, Literal
import math

OptionSide = Literal["call", "put"]

# ───────────────────────────────────────────────────────────────────────────────
# Utilities: Normal pdf/cdf and numerics
# ───────────────────────────────────────────────────────────────────────────────
_SQRT_2PI = math.sqrt(2.0 * math.pi)
_SQRT_TINY = 1e-12


def _phi(x: float) -> float:
    "Standard normal PDF."
    return math.exp(-0.5 * x * x) / _SQRT_2PI


def _Phi(x: float) -> float:
    "Standard normal CDF via erf."
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _d1_d2_spot(
    S: float, K: float, T: float, r: float, q: float, sigma: float
) -> Tuple[float, float]:
    if T <= 0.0 or sigma <= 0.0 or S <= 0.0 or K <= 0.0:
        return (
            float("inf") if S > K else -float("inf"),
            float("inf") if S > K else -float("inf"),
        )
    v = sigma * math.sqrt(T)
    m = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / v
    return m, m - v


def _d1_d2_forward(F: float, K: float, T: float, sigma: float) -> Tuple[float, float]:
    if T <= 0.0 or sigma <= 0.0 or F <= 0.0 or K <= 0.0:
        return (
            float("inf") if F > K else -float("inf"),
            float("inf") if F > K else -float("inf"),
        )
    v = sigma * math.sqrt(T)
    m = (math.log(F / K) + 0.5 * sigma * sigma * T) / v
    return m, m - v


# ───────────────────────────────────────────────────────────────────────────────
# Pricing: BSM (spot with continuous dividend yield q)
# C = S e^{-qT} Φ(d1) − K e^{-rT} Φ(d2)
# P = K e^{-rT} Φ(−d2) − S e^{-qT} Φ(−d1)
# ───────────────────────────────────────────────────────────────────────────────
def price_bsm(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    side: OptionSide = "call",
) -> float:
    if T <= 0.0 or sigma <= 0.0:
        intrinsic = max(0.0, S - K) if side == "call" else max(0.0, K - S)
        return intrinsic
    d1, d2 = _d1_d2_spot(S, K, T, r, q, sigma)
    df_r = math.exp(-r * T)
    df_q = math.exp(-q * T)
    if side == "call":
        return S * df_q * _Phi(d1) - K * df_r * _Phi(d2)
    return K * df_r * _Phi(-d2) - S * df_q * _Phi(-d1)


# ───────────────────────────────────────────────────────────────────────────────
# Pricing: Black '76 (forward/futures)
# C = e^{-rT}[F Φ(d1) − K Φ(d2)]
# P = e^{-rT}[K Φ(−d2) − F Φ(−d1)]
# ───────────────────────────────────────────────────────────────────────────────
def price_black76(
    F: float, K: float, T: float, r: float, sigma: float, side: OptionSide = "call"
) -> float:
    if T <= 0.0 or sigma <= 0.0:
        intrinsic = max(0.0, F - K) if side == "call" else max(0.0, K - F)
        return math.exp(-r * T) * intrinsic
    d1, d2 = _d1_d2_forward(F, K, T, sigma)
    df = math.exp(-r * T)
    if side == "call":
        return df * (F * _Phi(d1) - K * _Phi(d2))
    return df * (K * _Phi(-d2) - F * _Phi(-d1))


# ───────────────────────────────────────────────────────────────────────────────
# Greeks: BSM
# ───────────────────────────────────────────────────────────────────────────────
@dataclass
class Greeks:
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    vanna: float
    vomma: float


def greeks_bsm(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    side: OptionSide = "call",
) -> Greeks:
    if T <= 0.0 or sigma <= 0.0 or S <= 0.0 or K <= 0.0:
        intrinsic_delta = 0.0
        if T <= 0.0:
            if side == "call":
                intrinsic_delta = 1.0 if S > K else 0.0
            else:
                intrinsic_delta = -1.0 if S < K else 0.0
        return Greeks(intrinsic_delta, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    d1, d2 = _d1_d2_spot(S, K, T, r, q, sigma)
    df_r = math.exp(-r * T)
    df_q = math.exp(-q * T)
    sqrtT = math.sqrt(T)
    Nd1 = _Phi(d1)
    Nd2 = _Phi(d2)
    nd1 = _phi(d1)
    if side == "call":
        delta = df_q * Nd1
    else:
        delta = df_q * (Nd1 - 1.0)
    gamma = df_q * nd1 / (S * sigma * sqrtT)
    vega = S * df_q * nd1 * sqrtT
    theta_first = -(S * df_q * nd1 * sigma) / (2.0 * sqrtT)
    if side == "call":
        theta = theta_first - r * K * df_r * Nd2 + q * S * df_q * Nd1
    else:
        theta = theta_first + r * K * df_r * _Phi(-d2) - q * S * df_q * _Phi(-d1)
    if side == "call":
        rho = K * T * df_r * Nd2
    else:
        rho = -K * T * df_r * _Phi(-d2)
    vanna = df_q * nd1 * (1.0 - d1 / (sigma * sqrtT))
    vomma = vega * d1 * d2 / max(sigma, _SQRT_TINY)
    return Greeks(delta, gamma, vega, theta, rho, vanna, vomma)


# ───────────────────────────────────────────────────────────────────────────────
# Greeks: Black '76 (forward)
# ───────────────────────────────────────────────────────────────────────────────
@dataclass
class B76Greeks:
    delta_F: float
    gamma_F: float
    vega: float
    rho: float
    theta: float


def greeks_black76(
    F: float, K: float, T: float, r: float, sigma: float, side: OptionSide = "call"
) -> B76Greeks:
    if T <= 0.0 or sigma <= 0.0 or F <= 0.0 or K <= 0.0:
        return B76Greeks(0.0, 0.0, 0.0, 0.0, 0.0)
    d1, d2 = _d1_d2_forward(F, K, T, sigma)
    df = math.exp(-r * T)
    nd1 = _phi(d1)
    Nd1 = _Phi(d1)
    price = price_black76(F, K, T, r, sigma, side=side)
    sqrtT = math.sqrt(T)
    delta_F = df * (Nd1 if side == "call" else (Nd1 - 1.0))
    gamma_F = df * nd1 / (F * sigma * sqrtT)
    vega = df * F * nd1 * sqrtT
    rho = -T * price  # discount factor sensitivity
    theta = -r * price + df * 0.5 * F * nd1 * sigma / sqrtT  # approximation
    return B76Greeks(delta_F, gamma_F, vega, rho, theta)


# ───────────────────────────────────────────────────────────────────────────────
# Put–call parity residual (BSM)
# ───────────────────────────────────────────────────────────────────────────────
def parity_residual_bsm(
    S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0
) -> float:
    C = price_bsm(S, K, T, r, sigma, q, "call")
    P = price_bsm(S, K, T, r, sigma, q, "put")
    return C - P - (S * math.exp(-q * T) - K * math.exp(-r * T))


# ───────────────────────────────────────────────────────────────────────────────
# Wrapper aliases (stable public interface for external solvers)
# These provide a consistent parameter ordering (S,K,T,r,q,sigma, option)
# used by the implied volatility module so both reference the same pricing core.
# ───────────────────────────────────────────────────────────────────────────────
def bs_price(
    S: float,
    K: float,
    T: float,
    r: float,
    q: float,
    sigma: float,
    option: OptionSide = "call",
) -> float:
    """Alias pricing wrapper mapping to internal price_bsm.

    Parameter order differs from internal price_bsm to align with conventional
    (S,K,T,r,q,sigma) signatures used in some analytics references.
    """
    return price_bsm(S, K, T, r, sigma, q, side=option)


def bs_vega(S: float, K: float, T: float, r: float, q: float, sigma: float) -> float:
    """Closed‑form Black–Scholes vega (same for call/put).

    Uses the same formula as inside greeks_bsm to avoid drift.
    """
    if T <= 0.0 or sigma <= 0.0 or S <= 0.0 or K <= 0.0:
        return 0.0
    d1, _ = _d1_d2_spot(S, K, T, r, q, sigma)
    nd1 = _phi(d1)
    return S * math.exp(-q * T) * nd1 * math.sqrt(T)


def black76_price(
    F: float,
    K: float,
    T: float,
    r: float,
    q_ignored: float,
    sigma: float,
    option: OptionSide = "call",
) -> float:  # noqa: D401
    """Alias wrapper for price_black76 (signature aligned with bs_price).

    The extra q_ignored parameter keeps the same positional pattern
    (S,K,T,r,q,sigma) when called generically; q is not used in Black‑76.
    """
    return price_black76(F, K, T, r, sigma, side=option)


def black76_vega(
    F: float, K: float, T: float, r: float, q_ignored: float, sigma: float
) -> float:
    """Black‑76 vega (same for call/put) matching wrapper signature."""
    if T <= 0.0 or sigma <= 0.0 or F <= 0.0 or K <= 0.0:
        return 0.0
    d1, _ = _d1_d2_forward(F, K, T, sigma)
    nd1 = _phi(d1)
    return math.exp(-r * T) * F * nd1 * math.sqrt(T)


# ───────────────────────────────────────────────────────────────────────────────
# Implied volatility (bisection)
# ───────────────────────────────────────────────────────────────────────────────
def implied_vol_bsm(
    target_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    q: float = 0.0,
    side: OptionSide = "call",
    tol: float = 1e-8,
    max_iter: int = 200,
    sigma_lo: float = 1e-6,
    sigma_hi: float = 5.0,
) -> float:
    if T <= 0.0:
        return 0.0
    intrinsic = max(0.0, S - K) if side == "call" else max(0.0, K - S)
    if target_price < intrinsic:
        target_price = intrinsic
    lo, hi = sigma_lo, sigma_hi
    plo = price_bsm(S, K, T, r, lo, q, side)
    phi = price_bsm(S, K, T, r, hi, q, side)

    # SymbolicEquation-guided expansion cap reacts to how far the current
    # bracket prices are from the target, promoting stability in SAFE mode.
    se_hint = se41_numeric(
        DNA_states=[
            _clamp(abs(target_price - plo), 0.0, max(1.0, target_price + 1e-6)),
            _clamp(abs(phi - target_price), 0.0, max(1.0, target_price + 1e-6)),
            _clamp(hi - lo, 0.0, 10.0),
            _clamp(T, 0.0, 10.0),
            _clamp(sigma_hi - sigma_lo, 0.0, 10.0),
        ],
        harmonic_patterns=[1.0, 0.97, 1.08],
    )
    expansion_cap = max(5, min(20, int(8 + abs(se_hint.get("score", 0.5)) * 8)))

    n_expand = 0
    while phi < target_price and n_expand < expansion_cap:
        hi *= 2.0
        phi = price_bsm(S, K, T, r, hi, q, side)
        n_expand += 1
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        pmid = price_bsm(S, K, T, r, mid, q, side)
        if abs(pmid - target_price) <= tol:
            return mid
        if pmid < target_price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ───────────────────────────────────────────────────────────────────────────────
# Optional: SE41 diagnostic "coherence" score
# ───────────────────────────────────────────────────────────────────────────────
def se41_price_coherence(
    S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0
) -> float:
    num = se41_numeric(
        DNA_states=[
            1.0,
            float(S > 0),
            float(K > 0),
            _clamp(T, 0.0, 10.0),
            _clamp(abs(r), 0.0, 1.0),
            _clamp(sigma, 0.0, 5.0),
            _clamp(abs(q), 0.0, 1.0),
            1.11,
        ],
        harmonic_patterns=[1.0, 1.07, 0.97, 1.13],
    )
    score = num["score"] if isinstance(num, dict) and "score" in num else 0.5
    return _clamp(abs(score), 0.0, 1.0)


# ───────────────────────────────────────────────────────────────────────────────
# Public exports
# ───────────────────────────────────────────────────────────────────────────────
__all__ = [
    "price_bsm",
    "greeks_bsm",
    "parity_residual_bsm",
    "implied_vol_bsm",
    "price_black76",
    "greeks_black76",
    "Greeks",
    "B76Greeks",
    "se41_price_coherence",
    # Public stable wrappers for external modules
    "bs_price",
    "bs_vega",
    "black76_price",
    "black76_vega",
]

# ───────────────────────────────────────────────────────────────────────────────
# Quick self‑test / demo
# ───────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":  # pragma: no cover
    S, K, T, r, q, sigma = 100.0, 100.0, 0.5, 0.03, 0.01, 0.25
    for side in ("call", "put"):
        px = price_bsm(S, K, T, r, sigma, q, side)
        g = greeks_bsm(S, K, T, r, sigma, q, side)
        iv = implied_vol_bsm(px, S, K, T, r, q, side)
        print(
            f"{side.upper():>4}  BS price={px:8.4f}  IV(backsolved)={iv:6.4f}  Δ={g.delta: .4f} Γ={g.gamma: .6f} ν={g.vega: .4f}"
        )
    F = S * math.exp((r - q) * T)
    px_b76 = price_black76(F, K, T, r, sigma, "call")
    g_b76 = greeks_black76(F, K, T, r, sigma, "call")
    print(
        f"B76 CALL  price={px_b76:8.4f}  δ_F={g_b76.delta_F: .4f}  ν={g_b76.vega: .4f}"
    )
