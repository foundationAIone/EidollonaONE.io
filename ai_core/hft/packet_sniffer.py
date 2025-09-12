"""HFT Packet Sniffer (SE41-aligned lightweight simulation)

What / Purpose
--------------
Provide a deterministic, testable abstraction for measuring network capture
latencies (ingest -> decode -> dispatch) with rolling statistical quality
metrics (mean, p50, p90, p99, jitter, drop rate) feeding symbolic governance.

Why / Rationale
---------------
1. Governance: Feed latency quality into SE41 risk/uncertainty hints.
2. Strategy Impact: Latency tail (p99) often dominates arbitrage viability.
3. Observability: Deterministic rolling window for CI comparisons.
4. Safety: Fallback symbolic stubs keep module runnable sans core package.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Deque, Dict, Any, Optional
from collections import deque
import statistics
import random
import math

try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41, SE41Signals  # type: ignore
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    class SE41Signals:  # minimal stub
        def __init__(
            self, risk: float = 0.4, uncertainty: float = 0.4, coherence: float = 0.6
        ):
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
class PacketSample:
    recv_ns: int
    decode_ns: int
    dispatch_ns: int
    dropped: bool = False

    @property
    def total_ns(self) -> int:
        return self.recv_ns + self.decode_ns + self.dispatch_ns


@dataclass
class LatencyStats:
    count: int
    drops: int
    mean_ns: float
    p50_ns: float
    p90_ns: float
    p99_ns: float
    jitter_ns: float
    drop_rate: float
    se41: SE41Signals
    stability: float


class PacketSniffer:
    def __init__(
        self, window: int = 500, symbolic: Optional[SymbolicEquation41] = None
    ) -> None:
        self.window = max(10, window)
        self.samples: Deque[PacketSample] = deque()
        self.symbolic = symbolic or SymbolicEquation41()

    # Simulation ingestion -------------------------------------------------
    def ingest(
        self, recv_ns: int, decode_ns: int, dispatch_ns: int, dropped: bool = False
    ) -> None:
        self.samples.append(PacketSample(recv_ns, decode_ns, dispatch_ns, dropped))
        if len(self.samples) > self.window:
            self.samples.popleft()

    def simulate_random(
        self,
        n: int = 25,
        base_us: float = 120.0,
        jitter_us: float = 30.0,
        drop_prob: float = 0.005,
    ) -> None:
        for _ in range(n):
            total = random.gauss(base_us, jitter_us)
            total_ns = max(1000.0, total * 1000.0)  # microseconds -> nanoseconds
            recv = int(total_ns * random.uniform(0.3, 0.5))
            decode = int(total_ns * random.uniform(0.2, 0.4))
            dispatch = int(total_ns - recv - decode)
            self.ingest(recv, decode, dispatch, dropped=random.random() < drop_prob)

    # Analytics -------------------------------------------------------------
    def _percentile(self, data: List[int], q: float) -> float:
        if not data:
            return 0.0
        k = (len(data) - 1) * q
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(data[int(k)])
        d0 = data[f] * (c - k)
        d1 = data[c] * (k - f)
        return float(d0 + d1)

    def stats(self) -> LatencyStats:
        if not self.samples:
            se = self.symbolic.evaluate(
                assemble_se41_context(
                    risk_hint=0.4, uncertainty_hint=0.4, coherence_hint=0.6
                )
            )
            return LatencyStats(0, 0, 0, 0, 0, 0, 0, 0, se, 1.0)
        totals = [s.total_ns for s in self.samples if not s.dropped]
        drops = sum(1 for s in self.samples if s.dropped)
        count = len(self.samples)
        if not totals:
            mean = p50 = p90 = p99 = jitter = 0.0
        else:
            totals_sorted = sorted(totals)
            mean = statistics.mean(totals_sorted)
            p50 = self._percentile(totals_sorted, 0.50)
            p90 = self._percentile(totals_sorted, 0.90)
            p99 = self._percentile(totals_sorted, 0.99)
            jitter = statistics.pstdev(totals_sorted) if len(totals_sorted) > 1 else 0.0
        drop_rate = drops / count if count else 0.0
        # Map metrics to hints: high p99 & jitter & drop_rate => higher risk/uncertainty
        base_us = mean / 1000.0 if mean else 0.0
        risk_hint = _clamp01(0.05 + (p99 / 1e6) * 0.15 + drop_rate * 0.5)
        uncertainty_hint = _clamp01(
            0.15 + (jitter / mean if mean else 0.0) * 0.4 + drop_rate * 0.4
        )
        coherence_hint = _clamp01(0.9 - (p99 / 1e6) * 0.1 - drop_rate * 0.5)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={"hft": {"latency_mean_us": base_us, "drop_rate": drop_rate}},
            )
        )
        stability = _clamp01(1.0 - (se.risk + se.uncertainty) / 2.0)
        return LatencyStats(
            count=count,
            drops=drops,
            mean_ns=mean,
            p50_ns=p50,
            p90_ns=p90,
            p99_ns=p99,
            jitter_ns=jitter,
            drop_rate=drop_rate,
            se41=se,
            stability=stability,
        )

    def snapshot_dict(self) -> Dict[str, Any]:
        st = self.stats()
        d = asdict(st)
        d["se41"] = {
            "risk": st.se41.risk,
            "uncertainty": st.se41.uncertainty,
            "coherence": st.se41.coherence,
        }
        return d


def _selftest() -> int:  # pragma: no cover
    sniffer = PacketSniffer(window=50)
    sniffer.simulate_random(80)
    snap = sniffer.snapshot_dict()
    assert 0 <= snap["stability"] <= 1
    print("PacketSniffer selftest ok", snap["stability"])
    return 0


__all__ = ["PacketSniffer", "LatencyStats", "PacketSample"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    p = PacketSniffer()
    p.simulate_random(40)
    print(json.dumps(p.snapshot_dict(), indent=2))
