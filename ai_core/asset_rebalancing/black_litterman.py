"""Black-Litterman Allocation – SE41 v4.1+ aligned.

Implements simplified Black-Litterman posterior fusion:
  * Implied equilibrium returns via reverse optimization (from market cap weights)
  * Incorporates investor views (P, Q, Ω) -> posterior expected returns
  * Produces mean-variance style weights on posterior

Assumptions / Simplifications:
  - Uses scalar risk aversion tau (~0.05 default) for equilibrium scaling
  - If views matrix P invalid, falls back to equilibrium returns
  - Covariance regularized; if singular -> ridge + pseudo-inverse
  - All weights long-only (negative clipped & renormalized)

SE41 Integration:
  - Numeric synthesis & ethos gate; deny -> fallback to market caps (input w_mkt)
  - Hold -> return previous weights if provided
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple, List

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    from trading.helpers.se41_trading_gate import se41_numeric, ethos_decision  # type: ignore
except Exception:  # pragma: no cover

    def se41_numeric(**_kw):  # type: ignore
        return {"score": 0.5}

    def ethos_decision(_tx):  # type: ignore
        return {"decision": "allow"}


def _arr(x):
    if np is None:
        return None
    try:
        return np.asarray(x, dtype=float)
    except Exception:
        return None


def black_litterman_posterior(
    cov: Sequence[Sequence[float]],
    market_weights: Sequence[float],
    risk_aversion: float = 2.5,
    tau: float = 0.05,
    P: Optional[Sequence[Sequence[float]]] = None,
    Q: Optional[Sequence[float]] = None,
    omega: Optional[Sequence[Sequence[float]]] = None,
) -> Tuple[List[float], List[float]]:
    """Return (equilibrium_returns, posterior_returns).

    Falls back gracefully to uniform if numpy / inputs invalid.
    """
    if np is None:
        n = len(market_weights)
        return [0.0] * n, [0.0] * n
    w = _arr(market_weights)
    C = _arr(cov)
    if w is None or C is None:
        return [0.0] * len(market_weights), [0.0] * len(market_weights)
    n = len(w)
    if C.shape != (n, n):
        return [0.0] * n, [0.0] * n
    try:
        C_reg = C + np.eye(n) * 1e-6
        invC = np.linalg.pinv(C_reg, rcond=1e-8)
        # Reverse optimization (equilibrium returns)
        pi = risk_aversion * (C @ w)
        if P is None or Q is None:
            return pi.tolist(), pi.tolist()
        Pm = _arr(P)
        Qv = _arr(Q)
        if Pm is None or Qv is None:
            return pi.tolist(), pi.tolist()
        k, nP = Pm.shape
        if nP != n or Qv.shape[0] != k:
            return pi.tolist(), pi.tolist()
        if omega is None:
            Omega = np.diag(np.full(k, 1e-3))
        else:
            Omega = _arr(omega)
            if Omega is None or Omega.shape != (k, k):
                Omega = np.diag(np.full(k, 1e-3))
        # Posterior formula
        tauC = tau * C
        middle = np.linalg.pinv(Pm @ tauC @ Pm.T + Omega, rcond=1e-8)
        mu_post = pi + tauC @ Pm.T @ middle @ (Qv - Pm @ pi)
        return pi.tolist(), mu_post.tolist()
    except Exception:
        return [0.0] * len(market_weights), [0.0] * len(market_weights)


def black_litterman_weights(
    cov: Sequence[Sequence[float]],
    market_weights: Sequence[float],
    risk_aversion: float = 2.5,
    tau: float = 0.05,
    P: Optional[Sequence[Sequence[float]]] = None,
    Q: Optional[Sequence[float]] = None,
    omega: Optional[Sequence[Sequence[float]]] = None,
    previous_weights: Optional[Sequence[float]] = None,
) -> List[float]:
    """Compute long-only Black-Litterman allocation weights.

    Governance: ethos_decision may deny / hold. Deny -> market_weights fallback.
    """
    eq, post = black_litterman_posterior(
        cov, market_weights, risk_aversion, tau, P, Q, omega
    )
    n = len(eq)
    if n == 0:
        return []
    if np is None:
        return list(market_weights)
    try:
        C = _arr(cov)
        if C is None or C.shape != (n, n):
            return list(market_weights)
        post_arr = _arr(post)
        C_reg = C + np.eye(n) * 1e-6
        invC = np.linalg.pinv(C_reg, rcond=1e-8)
        raw = invC @ post_arr
        denom = raw.sum()
        if abs(denom) < 1e-12:
            w = np.asarray(market_weights, dtype=float)
        else:
            w = raw / denom
        w = np.clip(w, 0.0, None)
        s = w.sum()
        if s <= 0:
            w = np.asarray(market_weights, dtype=float)
        else:
            w = w / s
    except Exception:
        return list(market_weights)

    numeric = (
        se41_numeric(M_t=0.58, DNA_states=[1.0, float(n), risk_aversion, 1.08])
        if callable(se41_numeric)
        else {"score": 0.5}
    )
    gate = ethos_decision(
        {
            "scope": "asset_rebalancing",
            "op": "black_litterman",
            "numeric": getattr(numeric, "get", lambda *_: 0.5)("score", 0.5),
        }
    )
    decision = (
        gate.get("decision", "allow")
        if isinstance(gate, dict)
        else gate[0] if isinstance(gate, tuple) else "allow"
    )
    if decision == "deny":
        return list(market_weights)
    if (
        decision == "hold"
        and previous_weights is not None
        and len(previous_weights) == n
    ):
        return list(previous_weights)
    return [float(x) for x in w.tolist()]


__all__ = [
    "black_litterman_posterior",
    "black_litterman_weights",
]
