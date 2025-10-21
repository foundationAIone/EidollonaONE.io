"""Volume Analytics Engine (SE41)

What
----
Computes rolling participation rate, volume imbalance, session profile, VWAP
deviation, and burst detection; projects these into governance hints.

Why
---
1. Execution: Detect volume bursts to adjust aggressiveness.
2. Participation: Maintain target schedule vs realized flow.
3. Governance: Elevated burst + imbalance inflate uncertainty.
4. Conviction: VWAP deviation influences mean-reversion vs momentum stance.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Deque, Dict, Any, Optional
from collections import deque
import statistics
import time
import random

try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41, SE41Signals  # type: ignore
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    class SE41Signals:
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
class VolumeBar:
    price: float
    volume: float
    buy_volume: float
    sell_volume: float
    ts: float

    @property
    def vwap_value(self) -> float:
        return self.price * self.volume


@dataclass
class VolumeMetrics:
    participation: float
    imbalance: float
    vwap: float
    vwap_deviation: float
    burst_score: float
    stability: float
    se41: SE41Signals
    explain: str


class VolumeAnalyzer:
    def __init__(
        self,
        window: int = 240,
        symbolic: Optional[SymbolicEquation41] = None,
        target_participation: float = 0.12,
    ) -> None:
        self.window = max(20, window)
        self.symbolic = symbolic or SymbolicEquation41()
        self.target_participation = target_participation
        self._bars: Deque[VolumeBar] = deque()
        self._executed_volume: float = 0.0
        self._total_volume: float = 0.0

    def push(
        self, price: float, volume: float, buy_volume: float, sell_volume: float
    ) -> None:
        self._bars.append(
            VolumeBar(price, volume, buy_volume, sell_volume, time.time())
        )
        self._total_volume += volume
        self._executed_volume += (
            volume * 0.02
        )  # assume we transacted 2% of bar volume (example)
        if len(self._bars) > self.window:
            old = self._bars.popleft()
            se_decay = self.symbolic.evaluate(
                assemble_se41_context(
                    risk_hint=_clamp01(old.volume / max(1.0, volume * 2.0)),
                    uncertainty_hint=_clamp01(abs(old.price - self._bars[-1].price) / max(1.0, self._bars[-1].price)),
                    coherence_hint=_clamp01(self.target_participation),
                    extras={"decay": {"age": time.time() - old.ts}},
                )
            )
            decay = _clamp01(se_decay.coherence)
            self._total_volume = max(0.0, self._total_volume - old.volume * decay)
            self._executed_volume = max(
                0.0, self._executed_volume - old.volume * 0.02 * decay
            )

    def simulate_random(self, n: int = 50, base_price: float = 100.0) -> None:
        p = base_price
        for _ in range(n):
            p += random.uniform(-0.3, 0.3)
            vol = random.uniform(500, 1500)
            buy = vol * random.uniform(0.3, 0.7)
            self.push(p, vol, buy, vol - buy)

    def metrics(self) -> VolumeMetrics:
        bars = list(self._bars)
        if not bars:
            se = self.symbolic.evaluate(
                assemble_se41_context(
                    risk_hint=0.4, uncertainty_hint=0.4, coherence_hint=0.6
                )
            )
            return VolumeMetrics(0, 0, 0, 0, 0, 1.0, se, "empty")
        total_vol = sum(b.volume for b in bars)
        vwap = sum(b.vwap_value for b in bars) / max(1e-9, total_vol)
        last_price = bars[-1].price
        vwap_dev = (last_price - vwap) / vwap if vwap else 0.0
        imbalance = (
            sum(b.buy_volume for b in bars) - sum(b.sell_volume for b in bars)
        ) / max(1e-9, total_vol)
        participation = _clamp01(
            self._executed_volume
            / max(1e-9, self._total_volume)
            / self.target_participation
        )
        # Burst detection: compare latest volume to rolling mean/std
        vols = [b.volume for b in bars]
        mean_v = statistics.mean(vols)
        std_v = statistics.pstdev(vols) if len(vols) > 1 else 0.0
        burst_score = (
            0.0
            if std_v < 1e-12
            else (
                _clamp01((vols[-1] - mean_v) / (3 * std_v))
                if vols[-1] > mean_v
                else 0.0
            )
        )
        risk_hint = _clamp01(0.1 + burst_score * 0.4 + abs(vwap_dev) * 0.3)
        uncertainty_hint = _clamp01(0.2 + abs(imbalance) * 0.3 + burst_score * 0.3)
        coherence_hint = _clamp01(0.9 - burst_score * 0.4 - abs(imbalance) * 0.2)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={"volume": {"bars": len(bars)}},
            )
        )
        stability = _clamp01(1.0 - (se.risk + se.uncertainty) / 2.0)
        explain = f"part={participation:.2f} imb={imbalance:+.2f} vdev={vwap_dev:+.3f} burst={burst_score:.2f}"
        return VolumeMetrics(
            participation=participation,
            imbalance=imbalance,
            vwap=vwap,
            vwap_deviation=vwap_dev,
            burst_score=burst_score,
            stability=stability,
            se41=se,
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
    a = VolumeAnalyzer()
    a.simulate_random(60)
    snap = a.snapshot_dict()
    assert "vwap" in snap
    print("VolumeAnalyzer selftest", snap["stability"])
    return 0


__all__ = ["VolumeAnalyzer", "VolumeMetrics", "VolumeBar"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    v = VolumeAnalyzer()
    v.simulate_random(40)
    print(json.dumps(v.snapshot_dict(), indent=2))
