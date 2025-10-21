"""
Implied volatility solvers (Black–Scholes with dividends, Black‑76 futures).
SE41-aligned, numerically robust, bounded root finding with proven initial guesses.

References (conceptual formulas; no verbatim code copied):
- Black–Scholes model (continuous dividends) & option valuation forms (Wikipedia)
- Brenner & Subrahmanyam (1988) ATM approximation
- Corrado & Miller (1996) quadratic approximation (as summarized by Hallerbach 2004)
- Standard put–call parity with carry (discounted spot S*e^{-qT}, strike K*e^{-rT})

Design choices:
- Monotonicity of price in volatility (positive vega) ⇒ unique root.
- Brent-style bracket (bisection + secant) for robustness; optional guarded Newton for speed.
- High quality initial guess: ATM (Brenner–Subrahmanyam) else Corrado–Miller.
- No‑arbitrage bounds enforced before solving; early exits at boundaries.
- Optional se41_numeric alignment hook (harmless if unavailable).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Tuple
import math

# Reuse canonical pricing & vega from black_scholes_model to avoid drift
from .black_scholes_model import (
    bs_price as core_bs_price,
    bs_vega as core_bs_vega,
    black76_price as core_black76_price,
    black76_vega as core_black76_vega,
)

# ──────────────────────────────────────────────────────────────────────────────
# Optional SE41 alignment hook (non‑blocking)
# ──────────────────────────────────────────────────────────────────────────────
try:  # pragma: no cover
    from trading.helpers.se41_trading_gate import se41_numeric  # type: ignore
except Exception:  # pragma: no cover

    def se41_numeric(**_kw):  # type: ignore
        return 0.5


OptionType = Literal["call", "put"]
ModelType = Literal["bs", "black76"]
MethodType = Literal["brent", "newton"]


# ──────────────────────────────────────────────────────────────────────────────
# Math utilities
# ──────────────────────────────────────────────────────────────────────────────
def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _is_close(a: float, b: float, rtol: float = 1e-12, atol: float = 1e-12) -> bool:
    return abs(a - b) <= (atol + rtol * max(1.0, abs(a), abs(b)))


# ──────────────────────────────────────────────────────────────────────────────
# NOTE: We purposefully avoid redefining pricing/vega logic here; we import the
# canonical implementations from black_scholes_model so implied volatility and
# other modules remain perfectly synchronized.


# ──────────────────────────────────────────────────────────────────────────────
# No‑arbitrage bounds & initial guesses
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class PriceBounds:
    lower: float
    upper: float


def _bs_bounds(
    S: float, K: float, T: float, r: float, q: float, option: OptionType
) -> PriceBounds:
    Sd = S * math.exp(-q * T)
    X = K * math.exp(-r * T)
    if option == "call":
        return PriceBounds(max(Sd - X, 0.0), Sd)
    return PriceBounds(max(X - Sd, 0.0), X)


def _black76_bounds(
    F: float, K: float, T: float, r: float, option: OptionType
) -> PriceBounds:
    DF = math.exp(-r * T)
    if option == "call":
        return PriceBounds(max(DF * (F - K), 0.0), DF * F)
    return PriceBounds(max(DF * (K - F), 0.0), DF * K)


def _bs_initial_guess(
    price: float, S: float, K: float, T: float, r: float, q: float, option: OptionType
) -> float:
    if T <= 0.0:
        return 1e-9
    Sd = S * math.exp(-q * T)
    X = K * math.exp(-r * T)
    # Convert put price to synthetic call via parity if needed
    call_price = price + Sd - X if option == "put" else price
    fwd = S * math.exp((r - q) * T)
    if abs(K - fwd) <= 1e-6 * max(1.0, fwd):  # ATM forward → Brenner & Subrahmanyam
        atm = max(call_price, 1e-16)
        return math.sqrt(2.0 * math.pi / max(T, 1e-16)) * (atm / max(Sd, 1e-16))
    # Corrado–Miller quadratic approximation
    A = call_price - 0.5 * (S - X)
    B = S - X
    inside = A * A + (B * B) / math.pi
    sigma_sqrt_T = (math.sqrt(2.0 * math.pi) / (S + X)) * (
        A + math.sqrt(max(inside, 0.0))
    )
    return max(sigma_sqrt_T / math.sqrt(T), 1e-9)


# ──────────────────────────────────────────────────────────────────────────────
# Root-finding algorithms
# ──────────────────────────────────────────────────────────────────────────────
def _bracket(
    func: Callable[[float], float], lo: float, hi: float
) -> Tuple[float, float]:
    f_lo = func(lo)
    f_hi = func(hi)
    if f_lo == 0.0:
        return lo, lo
    if f_hi == 0.0:
        return hi, hi
    if f_lo * f_hi < 0.0:
        return lo, hi
    for _ in range(12):  # expand upward; price increases with sigma
        hi *= 2.0
        f_hi = func(hi)
        if f_lo * f_hi < 0.0 or f_hi == 0.0:
            return lo, hi
    return lo, hi


def _solve_brent(
    func: Callable[[float], float],
    lo: float,
    hi: float,
    tol: float = 1e-8,
    max_iter: int = 100,
) -> Tuple[float, bool, int]:
    a, b = lo, hi
    fa, fb = func(a), func(b)
    if fa == 0.0:
        return a, True, 0
    if fb == 0.0:
        return b, True, 0
    if fa * fb > 0.0:
        return b, False, 0
    c, fc = a, fa
    d = e = b - a
    for it in range(1, max_iter + 1):
        if fb == 0.0:
            return b, True, it
        if abs(fc) < abs(fb):  # ensure |f(b)| ≤ |f(c)|
            a, b, c = b, c, b
            fa, fb, fc = fb, fc, fb
        tol1 = 2.0 * math.ulp(1.0) * abs(b) + 0.5 * tol
        m = 0.5 * (c - b)
        if abs(m) <= tol1:
            return b, True, it
        if abs(e) >= tol1 and abs(fa) > abs(fb):  # secant-like step
            s = fb / fa
            p = s * (b - a)
            q = 1.0 - s
            if p > 0.0:
                q = -q
            p = abs(p)
            min1 = 3.0 * m * q - abs(tol1 * q)
            min2 = abs(e * q)
            if 2.0 * p < (min1 if min1 < min2 else min2):
                e, d = d, p / q
            else:
                d = m
                e = d
        else:  # bisection
            d = m
            e = d
        a, fa = b, fb
        if abs(d) > tol1:
            b += d
        else:
            b += math.copysign(tol1, m)
        fb = func(b)
        if (fb > 0 and fc > 0) or (fb < 0 and fc < 0):
            c, fc = a, fa
    return b, False, max_iter


def _solve_newton(
    func: Callable[[float], float],
    dfunc: Callable[[float], float],
    x0: float,
    bounds: Tuple[float, float],
    tol: float = 1e-8,
    max_iter: int = 50,
) -> Tuple[float, bool, int]:
    lo, hi = bounds
    x = min(max(x0, lo), hi)
    for it in range(1, max_iter + 1):
        fx = func(x)
        vx = dfunc(x)
        if vx <= 0.0 or not math.isfinite(vx):
            x = min(max((x + (lo + hi) * 0.5) * 0.5, lo), hi)
            continue
        step = fx / vx
        x_new = x - step
        if not (lo <= x_new <= hi) or not math.isfinite(x_new):
            x_new = min(max(x - step * 0.5, lo), hi)
        if abs(x_new - x) <= tol * max(1.0, abs(x)):
            return x_new, True, it
        if fx > 0.0:
            hi = min(hi, x_new)
        else:
            lo = max(lo, x_new)
        x = x_new
    return x, False, max_iter


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class IVResult:
    sigma: float
    converged: bool
    iterations: int
    method_used: str
    alignment_score: float = 0.0


def implied_volatility(
    price: float,
    S: float,
    K: float,
    T: float,
    r: float = 0.0,
    q: float = 0.0,
    option: OptionType = "call",
    model: ModelType = "bs",
    method: MethodType = "brent",
    bounds: Tuple[float, float] = (1e-9, 5.0),
    tol: float = 1e-8,
    max_iter: int = 100,
    return_full: bool = False,
) -> IVResult | float:
    if price < 0.0:
        raise ValueError("Option price must be non-negative.")
    if T <= 0.0:
        raise ValueError("Maturity T must be positive.")

    lo, hi = bounds
    if lo <= 0.0:
        lo = 1e-12

    if model == "bs":
        bnd = _bs_bounds(S, K, T, r, q, option)

        def price_fn(sig: float) -> float:
            return core_bs_price(S, K, T, r, q, sig, option)

        def vega_fn(sig: float) -> float:
            return core_bs_vega(S, K, T, r, q, sig)

        sigma0 = _bs_initial_guess(price, S, K, T, r, q, option)
    else:  # black76 path: treat S as F
        DF = math.exp(-r * T)
        F = S
        bnd = _black76_bounds(F, K, T, r, option)

        def price_fn(sig: float) -> float:
            return core_black76_price(F, K, T, r, 0.0, sig, option)

        def vega_fn(sig: float) -> float:
            return core_black76_vega(F, K, T, r, 0.0, sig)

        Sd, X = DF * F, DF * K
        A = price - 0.5 * (Sd - X)
        inside = A * A + (Sd - X) ** 2 / math.pi
        sigma0 = (math.sqrt(2.0 * math.pi) / (Sd + X)) * (
            A + math.sqrt(max(inside, 0.0))
        )
        sigma0 = max(sigma0 / math.sqrt(T), 1e-9)

    if price < bnd.lower - 1e-12 or price > bnd.upper + 1e-12:
        msg = (
            "Observed price "
            f"{price:.6g}"
            " is outside no-arbitrage bounds "
            f"[{bnd.lower:.6g}, {bnd.upper:.6g}] for {option}."
        )
        raise ValueError(msg)
    if _is_close(price, bnd.lower, atol=1e-12):
        res = IVResult(
            sigma=0.0,
            converged=True,
            iterations=0,
            method_used="bounds",
            alignment_score=0.0,
        )
        return res if return_full else res.sigma
    if _is_close(price, bnd.upper, atol=1e-12):
        res = IVResult(
            sigma=hi,
            converged=False,
            iterations=0,
            method_used="bounds_upper",
            alignment_score=0.0,
        )
        return res if return_full else res.sigma

    def residual(sig: float) -> float:
        return price_fn(sig) - price

    method_used = method
    converged = False
    iters = 0
    sigma = float(sigma0)

    # Optional alignment hint
    align = se41_numeric(
        M_t=0.5,
        DNA_states=[1.0, min(max(sigma0, 0.0), 1.0), 1.0, 1.11],
    )
    try:
        if isinstance(align, dict):
            align = float(next(iter(align.values())))
        align = float(align)
    except Exception:
        align = 0.5

    if method == "newton":
        sigma, converged, iters = _solve_newton(
            residual,
            vega_fn,
            sigma0,
            (lo, hi),
            tol=tol,
            max_iter=max_iter,
        )
        if not converged:
            method_used = "brent_fallback"
            a, b = _bracket(residual, lo, hi)
            sigma, converged, it_b = _solve_brent(
                residual,
                a,
                b,
                tol=tol,
                max_iter=max_iter,
            )
            iters += it_b
    else:
        a, b = _bracket(residual, lo, hi)
        sigma, converged, iters = _solve_brent(
            residual,
            a,
            b,
            tol=tol,
            max_iter=max_iter,
        )

    res = IVResult(
        sigma=max(sigma, lo),
        converged=converged,
        iterations=iters,
        method_used=method_used,
        alignment_score=float(align),
    )
    return res if return_full else res.sigma


__all__ = [
    "implied_volatility",
    "IVResult",
    # Expose underlying pricing/vega for validation
    # Re-export canonical pricing wrappers (imported, not defined here)
    "core_bs_price",
    "core_bs_vega",
    "core_black76_price",
    "core_black76_vega",
]


if __name__ == "__main__":  # pragma: no cover
    # Basic smoke tests
    iv = implied_volatility(
        price=5.20, S=100, K=100, T=0.5, r=0.02, q=0.01, option="call", model="bs"
    )
    print("BS IV", iv)
    fut_iv = implied_volatility(
        price=3.10,
        S=101.5,
        K=100,
        T=0.25,
        r=0.03,
        option="put",
        model="black76",
        method="newton",
        return_full=True,
    )
    print("B76 IV", fut_iv)
