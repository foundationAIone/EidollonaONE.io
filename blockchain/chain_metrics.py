"""Chain Metrics Adapter (Serplus)

Provides snapshot of on-chain / simulated metrics used by the Serplus
policy engine. Real implementation should integrate:
 - Reserves oracle (treasury assets valuation)
 - DEX TWAP oracle (e.g., Uniswap v3 or Chainlink)
 - Volatility estimator (price series)
 - Liquidity depth metrics

This stub supplies deterministic-ish pseudo-random values for development.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import time
import random


@dataclass
class ChainSnapshot:
    reserves_usd: float
    price_usd: float
    twap_usd: float
    realized_vol: float
    liquidity_score: float
    ts: float


def get_snapshot(symbol: str = "SRP", seed: Optional[int] = None) -> ChainSnapshot:
    if seed is not None:
        random.seed(seed)
    base_price = 1.00 + random.uniform(-0.01, 0.01)
    reserves = 1_000_000 + random.uniform(-20_000, 25_000)
    realized_vol = 0.10 + random.uniform(-0.02, 0.03)
    liquidity_score = 0.65 + random.uniform(-0.05, 0.05)
    return ChainSnapshot(
        reserves_usd=round(reserves, 2),
        price_usd=round(base_price, 4),
        twap_usd=round(base_price * (1 + random.uniform(-0.002, 0.002)), 4),
        realized_vol=round(realized_vol, 4),
        liquidity_score=round(liquidity_score, 4),
        ts=time.time(),
    )


__all__ = ["ChainSnapshot", "get_snapshot"]

if __name__ == "__main__":  # pragma: no cover
    print(get_snapshot(seed=42))
