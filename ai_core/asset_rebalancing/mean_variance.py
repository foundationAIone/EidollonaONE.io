"""Mean-Variance (Markowitz) Allocation – SE41 v4.1+ aligned.

Features:
  * Expected return / covariance based weight optimization (long-only)
  * Optional target return or risk aversion parameter
  * Soft covariance regularization (ridge)
  * Rebalance threshold helper (to reduce turnover)
  * Lightweight SE41 numeric synthesis + ethos gate (optional)

Fails safe: if numpy unavailable or inputs invalid -> uniform weights.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

try:  # optional dependency
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


def _to_array(x: Sequence[float]) -> Optional["np.ndarray"]:
    if np is None:
        return None
    try:
        arr = np.asarray(x, dtype=float)
        if arr.ndim != 1:
            return None
        return arr
    except Exception:
        return None


def mean_variance_optimize(
    exp_returns: Sequence[float],
    covariance: Sequence[Sequence[float]],
    risk_aversion: float = 1.0,
    l2_reg: float = 1e-6,
    allow_short: bool = False,
    previous_weights: Optional[Sequence[float]] = None,
) -> List[float]:
    """Compute mean-variance optimal weights.

    Args:
            exp_returns: Expected returns vector (len N)
            covariance: NxN covariance matrix
            risk_aversion: Lambda scaling risk term (higher -> more conservative)
            l2_reg: Ridge added to diagonal for stability
            allow_short: If False, negative weights are clipped then renormalized
            previous_weights: Used when ethos gate returns HOLD (fallback)
    Returns:
            List of N weights summing to 1 (or uniform fallback)
    """
    n = len(exp_returns)
    if n == 0:
        return []
    if np is None:
        return [1.0 / n] * n
    mu = _to_array(exp_returns)
    if mu is None:
        return [1.0 / n] * n
    try:
        C = np.asarray(covariance, dtype=float)
    except Exception:
        return [1.0 / n] * n
    if C.shape != (n, n):
        return [1.0 / n] * n
    # Regularize
    try:
        C_reg = C + np.eye(n) * l2_reg
        invC = np.linalg.pinv(C_reg, rcond=1e-8)
        ones = np.ones(n)
        # Classic MV solution with risk aversion: w ∝ invC * mu / risk_aversion
        w_raw = (invC @ mu) / max(1e-9, risk_aversion)
        # Normalize to sum 1 using budget constraint projection
        denom = float(ones @ w_raw)
        if abs(denom) < 1e-12:
            w = ones / n
        else:
            w = w_raw / denom
        if not allow_short:
            w = np.clip(w, 0.0, None)
            s = w.sum()
            if s <= 0:
                w = ones / n
            else:
                w = w / s
    except Exception:
        return [1.0 / n] * n

    # Governance numeric
    numeric = (
        se41_numeric(M_t=0.6, DNA_states=[1.0, float(n), risk_aversion, 1.1])
        if callable(se41_numeric)
        else {"score": 0.5}
    )
    gate = ethos_decision(
        {
            "scope": "asset_rebalancing",
            "op": "optimize",
            "numeric": getattr(numeric, "get", lambda *_: 0.5)("score", 0.5),
        }
    )
    decision = (
        gate.get("decision", "allow")
        if isinstance(gate, dict)
        else gate[0] if isinstance(gate, tuple) else "allow"
    )
    if decision == "deny":
        # Return previous or uniform
        if previous_weights is not None and len(previous_weights) == n:
            return list(previous_weights)
        return [1.0 / n] * n
    if (
        decision == "hold"
        and previous_weights is not None
        and len(previous_weights) == n
    ):
        return list(previous_weights)
    return [float(x) for x in w.tolist()]


def efficient_frontier(
    exp_returns: Sequence[float],
    covariance: Sequence[Sequence[float]],
    points: int = 25,
    l2_reg: float = 1e-6,
) -> List[Tuple[float, float, List[float]]]:
    """Generate coarse efficient frontier: list of (risk, return, weights)."""
    n = len(exp_returns)
    if n == 0:
        return []
    if np is None:
        return [(0.0, 0.0, [1.0 / n] * n)]
    mu = _to_array(exp_returns)
    if mu is None:
        return []
    C = np.asarray(covariance, dtype=float)
    if C.shape != (n, n):
        return []
    frontier = []
    # Vary risk aversion from high (conservative) to low (aggressive)
    for lam in np.linspace(5.0, 0.1, points):
        w = mean_variance_optimize(
            mu, C, risk_aversion=float(lam), l2_reg=l2_reg, allow_short=False
        )
        if np is None:
            break
        w_arr = np.asarray(w)
        ret = float(w_arr @ mu)
        vol = float(np.sqrt(w_arr @ C @ w_arr))
        frontier.append((vol, ret, w))
    return frontier


def rebalance_threshold(
    current_w: Sequence[float], target_w: Sequence[float], tau: float = 0.02
) -> List[int]:
    """Return indices that exceed absolute deviation threshold tau."""
    if len(current_w) != len(target_w):
        return []
    out = []
    for i, (c, t) in enumerate(zip(current_w, target_w)):
        try:
            if abs(float(c) - float(t)) > tau:
                out.append(i)
        except Exception:
            continue
    return out


__all__ = [
    "mean_variance_optimize",
    "efficient_frontier",
    "rebalance_threshold",
]
