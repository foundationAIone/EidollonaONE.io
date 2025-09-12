"""Market Sentiment Engine (SE41 aligned)

What
----
Multi-source (news/headlines/social) sentiment aggregator producing
confidence-weighted polarity, momentum, and dispersion metrics with rolling
window coherence scoring fed into Symbolic Equation 41 governance.

Why
---
1. Governance: Systemic narrative turbulence elevates uncertainty gating risk.
2. Allocation: Momentum & polarity shifts inform risk-on/off tilts.
3. Stability: Dispersion vs consensus aids conviction sizing.
4. Determinism: Rolling windows & normalization yield reproducible CI outputs.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Deque, Dict, Any, Optional
from collections import deque
import math
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
class SentimentPoint:
    polarity: float  # -1..1
    confidence: float  # 0..1
    source: str
    ts: float


@dataclass
class SentimentMetrics:
    polarity: float
    momentum: float
    dispersion: float
    consensus: float
    volume: int
    stability: float
    se41: SE41Signals
    explain: str


class SentimentEngine:
    def __init__(
        self, window: int = 300, symbolic: Optional[SymbolicEquation41] = None
    ) -> None:
        self.window = max(10, window)
        self.symbolic = symbolic or SymbolicEquation41()
        self._points: Deque[SentimentPoint] = deque()

    # Ingestion ------------------------------------------------------------
    def push(
        self,
        polarity: float,
        confidence: float,
        source: str,
        ts: Optional[float] = None,
    ) -> None:
        self._points.append(
            SentimentPoint(
                polarity=max(-1.0, min(1.0, polarity)),
                confidence=_clamp01(confidence),
                source=source,
                ts=ts or time.time(),
            )
        )
        if len(self._points) > self.window:
            self._points.popleft()

    def simulate_random(self, n: int = 30) -> None:
        for _ in range(n):
            self.push(
                polarity=random.uniform(-1, 1),
                confidence=random.uniform(0.3, 0.95),
                source=random.choice(["news", "social", "headline"]),
            )

    # Metrics --------------------------------------------------------------
    def metrics(self) -> SentimentMetrics:
        pts = list(self._points)
        if not pts:
            se = self.symbolic.evaluate(
                assemble_se41_context(
                    risk_hint=0.4, uncertainty_hint=0.4, coherence_hint=0.6
                )
            )
            return SentimentMetrics(0, 0, 0, 0, 0, 1.0, se, "empty")
        weights = [p.confidence for p in pts]
        wsum = sum(weights) or 1.0
        polarity = sum(p.polarity * p.confidence for p in pts) / wsum
        # Momentum: difference between latest average and average of first quartile
        q = max(1, len(pts) // 4)
        early = pts[:q]
        early_avg = sum(p.polarity * p.confidence for p in early) / max(
            1e-9, sum(p.confidence for p in early)
        )
        momentum = polarity - early_avg
        # Dispersion: weighted std
        mean_p = polarity
        variance = sum(p.confidence * (p.polarity - mean_p) ** 2 for p in pts) / wsum
        dispersion = math.sqrt(variance)
        consensus = 1.0 - min(1.0, dispersion)
        # Hints
        risk_hint = _clamp01(0.1 + abs(momentum) * 0.2)
        uncertainty_hint = _clamp01(0.2 + dispersion * 0.5)
        coherence_hint = _clamp01(0.85 - dispersion * 0.4)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={"sentiment": {"volume": len(pts)}},
            )
        )
        stability = _clamp01(1.0 - (se.risk + se.uncertainty) / 2.0)
        explain = f"pol={polarity:+.2f} mom={momentum:+.2f} disp={dispersion:.2f} cons={consensus:.2f}"
        return SentimentMetrics(
            polarity=polarity,
            momentum=momentum,
            dispersion=dispersion,
            consensus=consensus,
            volume=len(pts),
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
    eng = SentimentEngine()
    eng.simulate_random(50)
    snap = eng.snapshot_dict()
    assert "polarity" in snap
    print("SentimentEngine selftest", snap["stability"])
    return 0


__all__ = ["SentimentEngine", "SentimentMetrics", "SentimentPoint"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    e = SentimentEngine()
    e.simulate_random(30)
    print(json.dumps(e.snapshot_dict(), indent=2))
