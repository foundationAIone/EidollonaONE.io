"""Unified HFT Engine Orchestrator

What
----
Coordinates packet capture, co-location scoring, microstructure analytics,
and latency arbitrage modeling into a consolidated governance snapshot.

Why
---
1. Cohesion: Single call to obtain tactical readiness & opportunity map.
2. Governance: Aggregates risk/uncertainty across subsystems for SE41.
3. Extensibility: Replace any module with richer external implementation.
4. Deterministic: Supports CI by stable simulation seeding.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
import random
import time

from .packet_sniffer import PacketSniffer
from .co_location_manager import CoLocationManager
from .microstructure import MicrostructureAnalyzer
from .latency_arbitrage import LatencyArbitrageModel

try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41, SE41Signals  # type: ignore
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
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
class HFTOpportunity:
    leader: str
    laggard: str
    viability: float
    edge_bps: float
    explain: str


@dataclass
class HFTSnapshot:
    ts: float
    packet: Dict[str, Any]
    colocation: Dict[str, Any]
    micro: Dict[str, Any]
    opportunities: List[HFTOpportunity]
    se41: SE41Signals
    stability: float


class HFTEngine:
    def __init__(
        self, seed: Optional[int] = 1234, symbolic: Optional[SymbolicEquation41] = None
    ) -> None:
        if seed is not None:
            random.seed(seed)
        self.symbolic: Any = symbolic or SymbolicEquation41()
        self.sniffer = PacketSniffer(window=200, symbolic=self.symbolic)
        self.coloc = CoLocationManager(symbolic=self.symbolic)
        self.micro = MicrostructureAnalyzer(window=180, symbolic=self.symbolic)
        self.arb = LatencyArbitrageModel(symbolic=self.symbolic)
        # Default venues
        self.coloc.register("VENUE_A", 10)
        self.coloc.register("VENUE_B", 35)
        self.coloc.register("VENUE_C", 90)

    # Simulation cycle ----------------------------------------------------
    def simulate_cycle(self, ticks: int = 25) -> None:
        # Packet latency samples
        self.sniffer.simulate_random(ticks, base_us=120.0, jitter_us=25.0)
        # Co-location drift
        self.coloc.update_environment()
        # Microstructure
        self.micro.simulate_random(ticks)

    def snapshot(self) -> HFTSnapshot:
        packet = self.sniffer.snapshot_dict()
        coloc = self.coloc.snapshot_dict()
        micro = self.micro.snapshot_dict()
        # Compose risk hints across subsystems (simple blending)
        latency_risk = packet["se41"]["risk"]
        venue_risk = (
            max(f["se41"]["risk"] for f in coloc["facilities"].values())
            if coloc["facilities"]
            else 0.4
        )
        micro_risk = micro["se41"]["risk"]
        avg_risk = (latency_risk + venue_risk + micro_risk) / 3
        avg_unc = (packet["se41"]["uncertainty"] + micro["se41"]["uncertainty"]) / 2
        avg_coh = (packet["se41"]["coherence"] + micro["se41"]["coherence"]) / 2
        ctx = assemble_se41_context(
            risk_hint=avg_risk,
            uncertainty_hint=avg_unc,
            coherence_hint=avg_coh,
            extras={"hft": {"blend": True}},
        )
        se = self.symbolic.evaluate(ctx)
        stability = _clamp01(1.0 - (se.risk + se.uncertainty) / 2.0)
        # Opportunity extraction
        prices = {
            v: 100 + random.uniform(-0.15, 0.15) for v in coloc["facilities"].keys()
        }
        net_latency_us = (
            packet.get("p99_ns", 0) / 1000.0 if packet.get("p99_ns") else 300.0
        )
        opps = self.arb.evaluate(prices, net_latency_us, stability)
        hopps = [
            HFTOpportunity(o.leader, o.laggard, o.viability, o.edge_bps, o.explain)
            for o in opps[:5]
        ]
        return HFTSnapshot(
            ts=time.time(),
            packet=packet,
            colocation=coloc,
            micro=micro,
            opportunities=hopps,
            se41=se,
            stability=stability,
        )

    def snapshot_dict(self) -> Dict[str, Any]:
        snap = self.snapshot()
        return {
            "ts": snap.ts,
            "stability": snap.stability,
            "packet": snap.packet,
            "colocation": snap.colocation,
            "micro": snap.micro,
            "opportunities": [asdict(o) for o in snap.opportunities],
            "se41": {
                "risk": snap.se41.risk,
                "uncertainty": snap.se41.uncertainty,
                "coherence": snap.se41.coherence,
            },
        }


def _selftest() -> int:  # pragma: no cover
    eng = HFTEngine()
    eng.simulate_cycle()
    snap = eng.snapshot_dict()
    assert "packet" in snap and "micro" in snap and "opportunities" in snap
    print("HFTEngine selftest stability=", snap["stability"])
    return 0


__all__ = ["HFTEngine", "HFTSnapshot", "HFTOpportunity"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    e = HFTEngine()
    e.simulate_cycle()
    print(json.dumps(e.snapshot_dict(), indent=2))
