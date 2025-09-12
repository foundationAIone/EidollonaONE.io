"""Risk Parity Allocation – SE41 v4.1+ aligned.

Two approaches provided:
  * Closed-form approximation using inverse volatility (risk_parity_weights)
  * Iterative equal risk contribution solver (risk_parity_iterative)

Adds optional SE41 ethos gating (deny -> fall back to previous weights).
"""

from __future__ import annotations

from typing import List, Optional, Sequence

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


def risk_parity_weights(covariance: Sequence[Sequence[float]]) -> List[float]:
    """Inverse volatility heuristic -> normalize -> weights.

    Falls back to uniform if covariance invalid / numpy missing.
    """
    if covariance is None:
        return []
    if np is None:
        n = len(covariance)
        return [1.0 / n] * n if n else []
    try:
        C = np.asarray(covariance, dtype=float)
        if C.ndim != 2 or C.shape[0] != C.shape[1]:
            raise ValueError
        vol = np.sqrt(np.clip(np.diag(C), 1e-12, None))
        inv = 1.0 / vol
        w = inv / inv.sum()
        return [float(x) for x in w.tolist()]
    except Exception:
        n = len(covariance)
        return [1.0 / n] * n if n else []


def risk_parity_iterative(
    covariance: Sequence[Sequence[float]],
    max_iter: int = 500,
    tol: float = 1e-6,
    previous_weights: Optional[Sequence[float]] = None,
) -> List[float]:
    """Iterative Equal Risk Contribution (ERC) solver (long-only).

    Uses coordinate-style multiplicative updates. If SE41 ethos decision denies,
    returns previous or inverse-vol fallback.
    """
    if np is None:
        return risk_parity_weights(covariance)
    try:
        C = np.asarray(covariance, dtype=float)
        n = C.shape[0]
        if C.ndim != 2 or C.shape[1] != n:
            return risk_parity_weights(covariance)
        w = np.ones(n) / n
        target = 1.0 / n
        for _ in range(max_iter):
            portfolio_var = float(w @ C @ w)
            if portfolio_var <= 0:
                break
            mrc = C @ w  # marginal risk contribution
            rc = w * mrc
            total = rc.sum()
            if total <= 0:
                break
            # Desired RC = target * total -> adjust weights
            diff = rc / total - target
            if np.max(np.abs(diff)) < tol:
                break
            # Gradient-like update with clipping
            w *= 1 - diff
            w = np.clip(w, 1e-9, None)
            w /= w.sum()
    except Exception:
        return risk_parity_weights(covariance)

    numeric = (
        se41_numeric(M_t=0.55, DNA_states=[1.0, float(len(w)), 1.05])
        if callable(se41_numeric)
        else {"score": 0.5}
    )
    gate = ethos_decision(
        {
            "scope": "asset_rebalancing",
            "op": "risk_parity",
            "numeric": getattr(numeric, "get", lambda *_: 0.5)("score", 0.5),
        }
    )
    decision = (
        gate.get("decision", "allow")
        if isinstance(gate, dict)
        else gate[0] if isinstance(gate, tuple) else "allow"
    )
    if (
        decision == "deny"
        and previous_weights is not None
        and len(previous_weights) == len(w)
    ):
        return list(previous_weights)
    if decision == "deny":
        return risk_parity_weights(covariance)
    if (
        decision == "hold"
        and previous_weights is not None
        and len(previous_weights) == len(w)
    ):
        return list(previous_weights)
    return [float(x) for x in w.tolist()]


__all__ = [
    "risk_parity_weights",
    "risk_parity_iterative",
]
