"""Co-Location Manager (HFT)

What
----
Models venue data center proximity and dynamic relocation scoring.

Why
---
1. Latency Edge: Physical distance materially alters wire time; managing this
   adaptively helps sustain arbitrage viability.
2. Governance: Facility health & congestion feed risk/uncertainty for SE41.
3. Strategic Allocation: Score integrates cost vs benefit for relocation.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import time
import random

try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41, SE41Signals  # type: ignore
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    class SE41Signals:  # stub
        def __init__(self, risk=0.4, uncertainty=0.4, coherence=0.6):
            self.risk = risk
            self.uncertainty = uncertainty
            self.coherence = coherence

    class SymbolicEquation41:  # type: ignore
        def evaluate(self, ctx: Dict[str, Any]) -> SE41Signals:
            return SE41Signals(
                risk=ctx.get("risk_hint", 0.4),
                uncertainty=ctx.get("uncertainty_hint", 0.4),
                coherence=ctx.get("coherence_hint", 0.6),
            )

    def assemble_se41_context(**kw):
        return kw


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class VenueFacility:
    venue: str
    distance_km: float
    fiber_latency_us: float  # theoretical baseline one-way
    congestion: float  # 0..1
    outage_prob: float  # 0..1
    relocation_cost: float  # normalized cost weight
    se41: Optional[SE41Signals] = None
    stability: Optional[float] = None
    score: Optional[float] = None


@dataclass
class CoLocationSnapshot:
    ts: float
    facilities: Dict[str, VenueFacility]
    best: Optional[str]


class CoLocationManager:
    def __init__(self, symbolic: Optional[SymbolicEquation41] = None) -> None:
        self.symbolic = symbolic or SymbolicEquation41()
        self._facilities: Dict[str, VenueFacility] = {}

    def register(
        self,
        venue: str,
        distance_km: float,
        fiber_latency_us: Optional[float] = None,
        congestion: float = 0.2,
        outage_prob: float = 0.01,
        relocation_cost: float = 0.5,
    ) -> None:
        # Speed of light in fiber ~200,000 km/s => 5 microseconds per km (one-way) approx.
        base = fiber_latency_us if fiber_latency_us is not None else distance_km * 5.0
        self._facilities[venue] = VenueFacility(
            venue, distance_km, base, congestion, outage_prob, relocation_cost
        )

    def update_environment(self) -> None:
        # Simulate environment drift (would be replaced by real metrics)
        for fac in self._facilities.values():
            fac.congestion = _clamp01(fac.congestion + random.uniform(-0.05, 0.05))
            fac.outage_prob = _clamp01(fac.outage_prob + random.uniform(-0.01, 0.01))

    def evaluate(self, ctx: Optional[Dict[str, Any]] = None) -> CoLocationSnapshot:
        """Evaluate facility scores incorporating SE41 ethos alignment signals.

        Ethos/Alignment: congestion & outage probabilities push risk/uncertainty; coherence
        drops accordingly. Optional ctx merges higher-level governance hints.
        """
        best_id = None
        best_score = -1.0
        for vid, fac in self._facilities.items():
            # Hints: higher congestion & outage raise risk & uncertainty; distance raises latency penalty.
            risk_hint = _clamp01(0.1 + fac.outage_prob * 0.6 + fac.congestion * 0.3)
            uncertainty_hint = _clamp01(0.15 + fac.congestion * 0.5)
            coherence_hint = _clamp01(
                0.9 - fac.outage_prob * 0.7 - fac.congestion * 0.3
            )
            ctx_payload = assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={
                    "hft": {"venue": vid, "distance_km": fac.distance_km},
                    **(ctx or {}),
                },
            )
            se = self.symbolic.evaluate(ctx_payload)
            stability = _clamp01(1.0 - (se.risk + se.uncertainty) / 2.0)
            # Score: weight low latency, high stability, penalize cost; simple linear blend
            latency_factor = 1.0 - _clamp01(
                fac.fiber_latency_us / 1000.0
            )  # degrade after 1ms
            raw = (
                0.45 * latency_factor
                + 0.35 * stability
                + 0.2 * (1.0 - fac.relocation_cost)
            )
            fac.se41 = se
            fac.stability = stability
            fac.score = raw
            if raw > best_score:
                best_score = raw
                best_id = vid
        return CoLocationSnapshot(
            ts=time.time(),
            facilities={k: v for k, v in self._facilities.items()},
            best=best_id,
        )

    def snapshot_dict(self) -> Dict[str, Any]:
        snap = self.evaluate()
        return {
            "ts": snap.ts,
            "best": snap.best,
            "facilities": {
                k: {
                    **asdict(v),
                    "se41": (
                        {
                            "risk": v.se41.risk,
                            "uncertainty": v.se41.uncertainty,
                            "coherence": v.se41.coherence,
                        }
                        if v.se41
                        else None
                    ),
                }
                for k, v in snap.facilities.items()
            },
        }


def _selftest() -> int:  # pragma: no cover
    mgr = CoLocationManager()
    mgr.register("NYSE", 20)
    mgr.register("NASDAQ", 15)
    mgr.register("CME", 120)
    for _ in range(5):
        mgr.update_environment()
        mgr.evaluate()
    snap = mgr.snapshot_dict()
    assert snap["best"] in snap["facilities"]
    print("CoLocationManager selftest best=", snap["best"])
    return 0


__all__ = ["CoLocationManager", "CoLocationSnapshot", "VenueFacility"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    mgr = CoLocationManager()
    mgr.register("VENUEA", 5)
    mgr.register("VENUEB", 30)
    mgr.update_environment()
    print(json.dumps(mgr.snapshot_dict(), indent=2))
