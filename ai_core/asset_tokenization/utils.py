"""Utility helpers for asset_tokenization (SE41 aligned where relevant)."""

from __future__ import annotations

from typing import Dict, Iterable

try:
    from trading.helpers.se41_trading_gate import se41_numeric  # type: ignore
except Exception:  # pragma: no cover

    def se41_numeric(**_kw):  # type: ignore
        return {"score": 0.55}


def compute_supply_metrics(
    total_supply: float,
    circulating: float,
    velocity_samples: Iterable[float] | None = None,
) -> Dict:
    circulating = max(0.0, min(circulating, total_supply))
    velocity_samples = list(velocity_samples or [])
    avg_velocity = (
        sum(velocity_samples) / len(velocity_samples) if velocity_samples else 0.0
    )
    utilization = circulating / total_supply if total_supply > 0 else 0.0
    numeric = se41_numeric(M_t=0.58, DNA_states=[1.0, utilization, avg_velocity, 1.05])
    score = numeric.get("score", 0.55) if isinstance(numeric, dict) else 0.55
    return {
        "total_supply": total_supply,
        "circulating": circulating,
        "utilization": utilization,
        "avg_velocity": avg_velocity,
        "governance_score": score,
    }


def valuation_snapshot(
    symbol: str, price: float, supply_metrics: Dict, discount_rate: float = 0.0
) -> Dict:
    governance_adj = supply_metrics.get("governance_score", 0.55)
    base_value = price * supply_metrics.get("circulating", 0.0)
    # simple governance + discount factor (bounded)
    adjustment = 0.5 + min(max(governance_adj, 0.0), 1.5) * 0.3
    discount = 1.0 / (1.0 + max(discount_rate, 0.0))
    implied_value = base_value * adjustment * discount
    return {
        "symbol": symbol.upper(),
        "price": price,
        "circulating": supply_metrics.get("circulating", 0.0),
        "utilization": supply_metrics.get("utilization", 0.0),
        "governance_score": governance_adj,
        "implied_value": implied_value,
    }


__all__ = ["compute_supply_metrics", "valuation_snapshot"]
