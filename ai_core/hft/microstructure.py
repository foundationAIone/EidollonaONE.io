"""Microstructure Analytics (HFT)

What
----
Derives order book imbalance, spread dynamics, queue position decay, and
short-term volatility proxies for strategy selection & SE41 governance.

Why
---
1. Execution Quality: Imbalance + spread regime drives passive vs aggressive.
2. Risk Control: Fast widening spread lifts risk/uncertainty hints.
3. Latency Sensitivity: Queue decay modeling signals urgency.
4. Consistency: Rolling deterministic analytics for CI comparisons.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Deque, Dict, Any, Optional
from collections import deque
import statistics
import math
import time
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
class BookSample:
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    ts: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2 if (self.bid and self.ask) else 0.0

    @property
    def spread(self) -> float:
        return max(0.0, self.ask - self.bid)


@dataclass
class MicrostructureMetrics:
    imbalance: float
    spread: float
    spread_z: float
    realized_vol: float
    queue_decay: float
    se41: SE41Signals
    stability: float
    explain: str


class MicrostructureAnalyzer:
    def __init__(
        self, window: int = 120, symbolic: Optional[SymbolicEquation41] = None
    ) -> None:
        self.window = max(10, window)
        self.symbolic = symbolic or SymbolicEquation41()
        self._book: Deque[BookSample] = deque()

    def push(
        self,
        bid: float,
        ask: float,
        bid_size: float,
        ask_size: float,
        ts: Optional[float] = None,
    ) -> None:
        self._book.append(BookSample(bid, ask, bid_size, ask_size, ts or time.time()))
        if len(self._book) > self.window:
            self._book.popleft()

    def simulate_random(self, n: int = 30, base_mid: float = 100.0) -> None:
        mid = base_mid
        for _ in range(n):
            mid += random.uniform(-0.05, 0.05)
            spread = random.uniform(0.01, 0.05)
            bid = mid - spread / 2
            ask = mid + spread / 2
            bid_size = random.uniform(50, 200)
            ask_size = random.uniform(50, 200)
            self.push(bid, ask, bid_size, ask_size)

    def metrics(self) -> MicrostructureMetrics:
        if len(self._book) < 2:
            se = self.symbolic.evaluate(
                assemble_se41_context(
                    risk_hint=0.4, uncertainty_hint=0.4, coherence_hint=0.6
                )
            )
            return MicrostructureMetrics(
                imbalance=0.0,
                spread=0.0,
                spread_z=0.0,
                realized_vol=0.0,
                queue_decay=0.0,
                se41=se,
                stability=1.0,
                explain="empty",
            )
        spreads = [b.spread for b in self._book]
        spread = spreads[-1]
        mean_spread = statistics.mean(spreads)
        std_spread = statistics.pstdev(spreads) if len(spreads) > 1 else 0.0
        spread_z = (spread - mean_spread) / std_spread if std_spread > 1e-12 else 0.0
        mids = [b.mid for b in self._book]
        rets = []
        for i in range(1, len(mids)):
            if mids[i - 1]:
                rets.append(math.log(mids[i] / mids[i - 1]))
        realized_vol = (
            statistics.pstdev(rets) * math.sqrt(252 * 24 * 60) if len(rets) > 1 else 0.0
        )
        last = self._book[-1]
        imbalance = (
            (last.bid_size - last.ask_size) / (last.bid_size + last.ask_size)
            if (last.bid_size + last.ask_size)
            else 0.0
        )
        # Queue decay proxy: high vol + tight spread -> faster decay of queue advantage.
        queue_decay = _clamp01(abs(spread_z) * 0.3 + min(1.0, realized_vol / 2.0) * 0.5)
        risk_hint = _clamp01(0.1 + abs(spread_z) * 0.2 + queue_decay * 0.3)
        uncertainty_hint = _clamp01(0.2 + min(1.0, realized_vol / 3.0))
        coherence_hint = _clamp01(0.9 - abs(spread_z) * 0.15 - queue_decay * 0.3)
        ctx = assemble_se41_context(
            risk_hint=risk_hint,
            uncertainty_hint=uncertainty_hint,
            coherence_hint=coherence_hint,
            extras={"hft": {"spread": spread, "imbalance": imbalance}},
        )
        se = self.symbolic.evaluate(ctx)
        stability = _clamp01(1.0 - (se.risk + se.uncertainty) / 2.0)
        explain = f"imb={imbalance:+.2f} sz={spread_z:+.2f} qd={queue_decay:.2f} rv={realized_vol:.3f}"
        return MicrostructureMetrics(
            imbalance=imbalance,
            spread=spread,
            spread_z=spread_z,
            realized_vol=realized_vol,
            queue_decay=queue_decay,
            se41=se,
            stability=stability,
            explain=explain,
        )

    def snapshot_dict(self) -> Dict[str, Any]:
        m = self.metrics()
        d = asdict(m)
        d["se41"] = {
            "risk": m.se41.risk,
            "uncertainty": m.se41.uncertainty,
            "coherence": m.se41.coherence,
        }
        return d


def _selftest() -> int:  # pragma: no cover
    a = MicrostructureAnalyzer()
    a.simulate_random(60)
    snap = a.snapshot_dict()
    assert "spread" in snap
    print("MicrostructureAnalyzer selftest", snap["stability"])
    return 0


__all__ = ["MicrostructureAnalyzer", "MicrostructureMetrics", "BookSample"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    a = MicrostructureAnalyzer()
    a.simulate_random(40)
    print(json.dumps(a.snapshot_dict(), indent=2))
