"""Latency Arbitrage Model

What
----
Evaluates synthetic cross‑venue price leads/lags to score actionable latency
arbitrage potential, integrating packet and co-location health metrics via
provided adapters.

Why
---
1. Decision Support: Quantify edge size vs latency penalty.
2. Governance: High uncertainty from network elevates required spread edge.
3. Modularity: Plug in external PacketSniffer / CoLocationManager snapshots.
4. Determinism: Stable simulation path for CI.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
import random

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
class ArbOpportunity:
    leader: str
    laggard: str
    edge_bps: float
    expected_latency_us: float
    decay_factor: float
    symbolic: SE41Signals
    viability: float  # normalized viability score
    explain: str


class LatencyArbitrageModel:
    def __init__(self, symbolic: Optional[SymbolicEquation41] = None) -> None:
        self.symbolic = symbolic or SymbolicEquation41()

    def evaluate(
        self,
        prices: Dict[str, float],
        network_latency_us: float,
        stability: float,
        min_edge_bps: float = 2.0,
        ctx: Optional[Dict[str, Any]] = None,
    ) -> List[ArbOpportunity]:
        """Score latency arbitrage opportunities.

        Ethos/Alignment: network instability & latency inflate risk/uncertainty; optional
        ctx merges upstream governance hints for composite SE41 evaluation.
        """
        venues = list(prices.keys())
        out: List[ArbOpportunity] = []
        for i in range(len(venues)):
            for j in range(i + 1, len(venues)):
                a, b = venues[i], venues[j]
                pa, pb = prices[a], prices[b]
                if pa <= 0 or pb <= 0:
                    continue
                edge = (pa - pb) / ((pa + pb) / 2) * 10_000  # bps
                leader, laggard, edge_bps = (a, b, edge) if edge > 0 else (b, a, -edge)
                if edge_bps < min_edge_bps:  # insufficient raw edge
                    continue
                # Latency decay: edge significance erodes with network delay
                decay = 1.0 / (
                    1.0 + (network_latency_us / 500.0)
                )  # half-life around 500us
                risk_hint = _clamp01(0.1 + (network_latency_us / 2000.0))
                uncertainty_hint = _clamp01(0.2 + (1.0 - stability) * 0.5)
                coherence_hint = _clamp01(0.9 - (network_latency_us / 5000.0))
                ctx_payload = assemble_se41_context(
                    risk_hint=risk_hint,
                    uncertainty_hint=uncertainty_hint,
                    coherence_hint=coherence_hint,
                    extras={
                        "hft": {
                            "leader": leader,
                            "laggard": laggard,
                            "edge_bps": edge_bps,
                        },
                        **(ctx or {}),
                    },
                )
                se = self.symbolic.evaluate(ctx_payload)
                viability = _clamp01((edge_bps / 10.0) * decay * (se.coherence))
                out.append(
                    ArbOpportunity(
                        leader,
                        laggard,
                        edge_bps,
                        network_latency_us,
                        decay,
                        se,
                        viability,
                        explain=f"edge={edge_bps:.2f}bps decay={decay:.3f} risk={se.risk:.2f}",
                    )
                )
        # Sort by descending viability
        out.sort(key=lambda o: o.viability, reverse=True)
        return out

    def simulate(self, venues: List[str]) -> List[ArbOpportunity]:
        prices = {v: 100 + random.uniform(-0.2, 0.2) for v in venues}
        net_latency = random.uniform(50, 800)
        stability = random.uniform(0.5, 0.95)
        return self.evaluate(prices, net_latency, stability)


def _selftest() -> int:  # pragma: no cover
    model = LatencyArbitrageModel()
    opps = model.simulate(["VENUE1", "VENUE2", "VENUE3"])
    if opps:
        print("Top opp:", asdict(opps[0]))
    return 0


__all__ = ["LatencyArbitrageModel", "ArbOpportunity"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    m = LatencyArbitrageModel()
    print(json.dumps([asdict(o) for o in m.simulate(["A", "B", "C"])], indent=2))
