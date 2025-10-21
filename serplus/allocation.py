from __future__ import annotations

from typing import Any, Dict, List, Tuple

from serplus.ledger import ndjson_ledger as ledger

DEFAULT_BUCKETS: Dict[str, float] = {
    "treasury": 0.40,
    "operations": 0.20,
    "ecosystem": 0.15,
    "community": 0.15,
    "risk_buffer": 0.10,
}


def _normalize_weights(buckets: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, float(v)) for v in buckets.values())
    if total <= 0:
        raise ValueError("allocation weights must sum to > 0")
    return {k: max(0.0, float(v)) / total for k, v in buckets.items()}


def plan_allocation(amount: float, buckets: Dict[str, float] | None = None, decimals: int = 2) -> Dict[str, float]:
    weights = _normalize_weights(buckets or DEFAULT_BUCKETS)
    amt = round(float(amount), max(0, int(decimals)))
    return {bucket: round(amt * weight, decimals) for bucket, weight in weights.items()}


def _sorted_balances(balances: Dict[str, float]) -> List[Tuple[str, float]]:
    return sorted(balances.items(), key=lambda item: item[1], reverse=True)


def ledger_snapshot(asset: str = "SER", limit: int = 10) -> Dict[str, Any]:
    balances = ledger.balances(asset)
    total = sum(v for v in balances.values() if v > 0)
    entries = [
        {
            "account": account,
            "balance": amount,
            "share": 0.0 if total <= 0 else round(amount / total, 4),
        }
        for account, amount in _sorted_balances(balances)[: max(1, limit)]
    ]
    return {
        "asset": asset,
        "total_positive": round(total, 2),
        "holders": entries,
    }


def allocation_health(asset: str = "SER") -> Dict[str, Any]:
    balances = ledger.balances(asset)
    supply = max(ledger.total_supply(asset), 1e-9)
    concentration = max(balances.values() or [0.0]) / supply
    return {
        "asset": asset,
        "supply": round(supply, 2),
        "holder_count": len(balances),
        "concentration_ratio": round(concentration, 4),
    }


__all__ = [
    "DEFAULT_BUCKETS",
    "plan_allocation",
    "ledger_snapshot",
    "allocation_health",
]
