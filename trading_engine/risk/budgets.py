from __future__ import annotations

from typing import Dict

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - dev fallback
    def audit(event: str, **payload):  # type: ignore
        return None


def theta_budget(max_theta: float) -> Dict[str, float]:
    cap = abs(float(max_theta))
    audit("risk_budget_theta", cap=cap)
    return {"theta": cap}


def gamma_budget(max_gamma: float) -> Dict[str, float]:
    cap = abs(float(max_gamma))
    audit("risk_budget_gamma", cap=cap)
    return {"gamma": cap}


def var_cap(max_var: float) -> Dict[str, float]:
    cap = max(0.0, float(max_var))
    audit("risk_budget_var", cap=cap)
    return {"var": cap}


def enforce_budgets(positions: Dict[str, float], greeks: Dict[str, float], caps: Dict[str, float]) -> Dict[str, float]:
    """Scale positions to satisfy theta/gamma/var caps."""
    if not positions:
        return {}
    scale = 1.0
    for key, cap in caps.items():
        cap_val = abs(float(cap))
        if cap_val <= 0:
            continue
        current = abs(float(greeks.get(key, 0.0)))
        if current <= cap_val:
            continue
        scale = min(scale, cap_val / max(current, 1e-9))
    if scale >= 1.0:
        audit("risk_budgets_enforce", scaled=False, scale=1.0)
        return dict(positions)
    adjusted = {symbol: qty * scale for symbol, qty in positions.items()}
    audit("risk_budgets_enforce", scaled=True, scale=scale)
    return adjusted


__all__ = [
    "theta_budget",
    "gamma_budget",
    "var_cap",
    "enforce_budgets",
]
