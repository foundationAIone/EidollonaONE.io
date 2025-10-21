"""Quote offset helper inspired by Avellaneda–Stoikov."""

from __future__ import annotations


def quote_offset_bps(spread_bps: float, volatility: float, inventory: float, inv_aversion: float = 0.3) -> float:
    return max(0.5, spread_bps / 2.0 + 2.0 * volatility - inv_aversion * abs(inventory))
