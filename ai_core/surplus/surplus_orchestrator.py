"""Surplus Orchestrator (Composite)

What
----
Aggregates forecasting, liquidity buffer sizing, reserve sub-allocation,
treasury surplus distribution, and initiative ROI into a unified snapshot.

Why
---
1. Single entry for dashboards / API.
2. Ensures consistent governance signals across components.
3. Facilitates audit via structured snapshot with explanations.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
from .treasury_allocator import TreasuryAllocator
from .surplus_forecaster import SurplusForecaster
from .liquidity_buffer import LiquidityBufferModel
from .reserve_strategy import ReserveStrategyAllocator
from .initiative_roi import InitiativeROITracker


@dataclass
class SurplusSnapshot:
    forecast: Dict[str, Any]
    treasury_allocation: Dict[str, Any]
    liquidity: Dict[str, Any]
    reserve: Dict[str, Any]
    initiatives: Dict[str, Any]
    meta: Dict[str, Any]


class SurplusOrchestrator:
    def __init__(self) -> None:
        self.forecaster = SurplusForecaster()
        self.treasury = TreasuryAllocator()
        self.liquidity = LiquidityBufferModel()
        self.reserve = ReserveStrategyAllocator()
        self.initiatives = InitiativeROITracker()

    def record_initiative(
        self,
        name: str,
        invested: float,
        returns: float,
        risk: float,
        uncertainty: float,
        coherence: float,
    ) -> None:
        self.initiatives.update(name, invested, returns, risk, uncertainty, coherence)

    def snapshot(
        self,
        revenues: List[float],
        expenses: List[float],
        net_outflows: List[float],
        surplus_total: float,
        market_stress: float = 0.2,
        volatility_index: float = 0.15,
    ) -> SurplusSnapshot:
        fc = self.forecaster.forecast(revenues, expenses, steps=3)
        alloc = self.treasury.allocate(surplus_total, volatility_index=volatility_index)
        liq = self.liquidity.compute(net_outflows)
        res_alloc = self.reserve.allocate(
            alloc.weights.get("Reserve", surplus_total * 0.2),
            market_stress=market_stress,
        )
        lb = self.initiatives.leaderboard(10)
        snapshot = SurplusSnapshot(
            forecast={
                "values": fc.forecast,
                "lower": fc.lower,
                "upper": fc.upper,
                "explain": fc.explain,
            },
            treasury_allocation={"weights": alloc.weights, "explain": alloc.explain},
            liquidity={
                "target": liq.target_buffer,
                "stress_p95": liq.stress_p95,
                "explain": liq.explain,
            },
            reserve={"buckets": res_alloc.buckets, "explain": res_alloc.explain},
            initiatives={"leaderboard": lb},
            meta={
                "stability_hint": round(
                    1 - (alloc.se41.risk + alloc.se41.uncertainty) / 2, 3
                )
            },
        )
        return snapshot


__all__ = ["SurplusOrchestrator", "SurplusSnapshot"]


def _selftest() -> int:  # pragma: no cover
    orch = SurplusOrchestrator()
    orch.record_initiative("R&D_AI", 100, 130, 0.3, 0.25, 0.85)
    snap = orch.snapshot([100, 110, 115], [60, 62, 63], [10, 12, 11, 13, 9], 500)
    assert "forecast" in snap.__dict__
    print("SurplusOrchestrator selftest", snap.meta)
    return 0


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(_selftest())
    o = SurplusOrchestrator()
    print(
        json.dumps(
            o.snapshot([100, 110], [60, 63], [10, 11, 9], 400).__dict__,
            indent=2,
            default=str,
        )
    )
