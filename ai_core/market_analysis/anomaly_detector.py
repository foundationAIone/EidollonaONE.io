"""Market Anomaly Detector (SE41 integrated)

What
----
Combines robust z-score, median absolute deviation (MAD), and adaptive
volatility envelope breach logic to flag statistical price & volume anomalies.

Why
---
1. Risk Escalation: Persistent anomalies raise risk/uncertainty gating.
2. Strategy Guard: Suspends fragile strategies during structural breaks.
3. Monitoring: Deterministic metrics for alerting & CI snapshot tests.
4. Governance: Maps anomaly pressure into symbolic coherence adjustments.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Deque, List, Dict, Any, Optional
from collections import deque
import statistics
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
class AnomalyEvent:
    ts: float
    price_z: float
    volume_z: float
    envelope_breach: bool
    composite_score: float


@dataclass
class AnomalySnapshot:
    ts: float
    pressure: float
    events: List[AnomalyEvent]
    se41: SE41Signals
    stability: float
    explain: str


class AnomalyDetector:
    def __init__(
        self, window: int = 400, symbolic: Optional[SymbolicEquation41] = None
    ) -> None:
        self.window = max(20, window)
        self.symbolic = symbolic or SymbolicEquation41()
        self._prices: Deque[float] = deque()
        self._volumes: Deque[float] = deque()
        self._events: Deque[AnomalyEvent] = deque()

    def push(self, price: float, volume: float) -> None:
        self._prices.append(price)
        self._volumes.append(volume)
        if len(self._prices) > self.window:
            self._prices.popleft()
        if len(self._volumes) > self.window:
            self._volumes.popleft()
        self._evaluate_latest()

    def simulate_random(self, n: int = 60, base_price: float = 100.0) -> None:
        p = base_price
        for _ in range(n):
            p += random.uniform(-0.5, 0.5)
            vol = random.uniform(800, 1200)
            if random.random() < 0.05:  # spike
                p += random.uniform(-3, 3)
                vol *= random.uniform(2, 4)
            self.push(p, vol)

    def _z_score(self, data: List[float], value: float) -> float:
        if len(data) < 2:
            return 0.0
        m = statistics.mean(data)
        sd = statistics.pstdev(data)
        if sd < 1e-12:
            return 0.0
        return (value - m) / sd

    def _mad_score(self, data: List[float], value: float) -> float:
        if len(data) < 3:
            return 0.0
        median = statistics.median(data)
        mad = statistics.median([abs(x - median) for x in data])
        if mad < 1e-12:
            return 0.0
        return (value - median) / (1.4826 * mad)

    def _evaluate_latest(self) -> None:
        prices = list(self._prices)
        vols = list(self._volumes)
        if not prices:
            return
        latest_p = prices[-1]
        latest_v = vols[-1]
        price_z = self._z_score(prices, latest_p)
        volume_z = self._z_score(vols, latest_v)
        # Envelope using rolling mean +/- k * rolling std
        if len(prices) > 10:
            m = statistics.mean(prices)
            sd = statistics.pstdev(prices) or 1.0
            envelope_breach = latest_p > m + 2.5 * sd or latest_p < m - 2.5 * sd
        else:
            envelope_breach = False
        mad_price = self._mad_score(prices, latest_p)
        comp = _clamp01(
            (abs(price_z) + abs(mad_price) * 0.7 + max(0.0, volume_z) * 0.5) / 6.0
        )
        if comp > 0.35 or envelope_breach:
            evt = AnomalyEvent(
                ts=time.time(),
                price_z=price_z,
                volume_z=volume_z,
                envelope_breach=envelope_breach,
                composite_score=comp,
            )
            self._events.append(evt)
            if len(self._events) > self.window:
                self._events.popleft()

    def snapshot(self) -> AnomalySnapshot:
        events = list(self._events)
        pressure = (
            0.0
            if not events
            else sum(e.composite_score for e in events[-min(25, len(events)) :]) / 25.0
        )
        risk_hint = _clamp01(0.1 + pressure * 0.6)
        uncertainty_hint = _clamp01(0.2 + pressure * 0.5)
        coherence_hint = _clamp01(0.9 - pressure * 0.7)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={"anomaly": {"recent_events": len(events)}},
            )
        )
        stability = _clamp01(1.0 - (se.risk + se.uncertainty) / 2.0)
        explain = f"pressure={pressure:.3f} events={len(events)}"
        return AnomalySnapshot(
            ts=time.time(),
            pressure=pressure,
            events=events[-10:],
            se41=se,
            stability=stability,
            explain=explain,
        )

    def snapshot_dict(self) -> Dict[str, Any]:
        snap = self.snapshot()
        return {
            "ts": snap.ts,
            "pressure": snap.pressure,
            "stability": snap.stability,
            "events": [asdict(e) for e in snap.events],
            "se41": {
                "risk": snap.se41.risk,
                "uncertainty": snap.se41.uncertainty,
                "coherence": snap.se41.coherence,
            },
            "explain": snap.explain,
        }


def _selftest() -> int:  # pragma: no cover
    d = AnomalyDetector()
    d.simulate_random(120)
    s = d.snapshot_dict()
    assert "pressure" in s
    print("AnomalyDetector selftest", s["pressure"])
    return 0


__all__ = ["AnomalyDetector", "AnomalySnapshot", "AnomalyEvent"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    d = AnomalyDetector()
    d.simulate_random(80)
    print(json.dumps(d.snapshot_dict(), indent=2))
