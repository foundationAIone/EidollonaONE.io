"""Market Profile (TPO/Value Area) Engine (SE41)

What
----
Constructs a time-price-opportunity style distribution (coarse bins) to derive
value area (VAH, VAL), point of control (POC), kurtosis, and balance metrics.

Why
---
1. Context: Over/under value area guides bias & inventory decisions.
2. Regime: Kurtosis & balance ratio signal transition to trend/volatile states.
3. Governance: Unbalanced distributions raise uncertainty gating.
4. Determinism: Fixed bin schema & normalization for reproducible CI output.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
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
class ProfileMetrics:
    poc: float
    vah: float
    val: float
    kurtosis: float
    balance: float
    stability: float
    se41: SE41Signals
    explain: str


class MarketProfile:
    def __init__(
        self, bins: int = 40, symbolic: Optional[SymbolicEquation41] = None
    ) -> None:
        self.bins = max(10, bins)
        self.symbolic = symbolic or SymbolicEquation41()
        self._prices: List[float] = []

    def push(self, price: float) -> None:
        self._prices.append(price)
        if len(self._prices) > 5000:
            self._prices = self._prices[-5000:]

    def simulate_random(self, n: int = 400, base: float = 100.0) -> None:
        p = base
        for _ in range(n):
            p += random.uniform(-0.4, 0.4)
            self.push(p)

    def _distribution(self) -> Dict[str, Any]:
        if not self._prices:
            return {"hist": [], "edges": [], "min": 0.0, "max": 0.0}
        lo = min(self._prices)
        hi = max(self._prices)
        if hi - lo < 1e-9:
            hi = lo + 1e-6
        step = (hi - lo) / self.bins
        hist = [0] * self.bins
        for px in self._prices:
            idx = min(self.bins - 1, int((px - lo) / step))
            hist[idx] += 1
        edges = [lo + i * step for i in range(self.bins + 1)]
        return {"hist": hist, "edges": edges, "min": lo, "max": hi}

    def metrics(self) -> ProfileMetrics:
        d = self._distribution()
        hist = d["hist"]
        if not hist:
            se = self.symbolic.evaluate(
                assemble_se41_context(
                    risk_hint=0.4, uncertainty_hint=0.4, coherence_hint=0.6
                )
            )
            return ProfileMetrics(0, 0, 0, 0, 0, 1.0, se, "empty")
        total = sum(hist)
        probs = [h / total for h in hist]
        # POC
        poc_idx = max(range(len(hist)), key=lambda i: hist[i])
        edges = d["edges"]
        poc_price = (edges[poc_idx] + edges[poc_idx + 1]) / 2
        # Value area: expand around POC to capture 70% of volume
        target = 0.7 * total
        acc = hist[poc_idx]
        left = right = poc_idx
        while acc < target and (left > 0 or right < len(hist) - 1):
            left_prob = hist[left - 1] if left > 0 else -1
            right_prob = hist[right + 1] if right < len(hist) - 1 else -1
            if right_prob >= left_prob:
                if right < len(hist) - 1:
                    right += 1
                    acc += hist[right]
            else:
                if left > 0:
                    left -= 1
                    acc += hist[left]
        val = (edges[left] + edges[left + 1]) / 2
        vah = (edges[right] + edges[right + 1]) / 2
        # Kurtosis (coarse): sum((x-mean)^4)/n / (var^2)
        centers = [(edges[i] + edges[i + 1]) / 2 for i in range(len(hist))]
        mean = sum(c * hist[i] for i, c in enumerate(centers)) / total
        var = sum(hist[i] * (centers[i] - mean) ** 2 for i in range(len(hist))) / total
        if var < 1e-12:
            kurt = 0.0
        else:
            fourth = (
                sum(hist[i] * (centers[i] - mean) ** 4 for i in range(len(hist)))
                / total
            )
            kurt = fourth / (var * var)
        # Balance: ratio of volume inside VA vs outside (already target ~0.7)
        balance = acc / total  # should be ~0.7
        # Hints
        imbalance_width = (vah - val) / (d["max"] - d["min"] + 1e-9)
        risk_hint = _clamp01(0.1 + (kurt / 10.0) + imbalance_width * 0.2)
        uncertainty_hint = _clamp01(0.2 + abs(balance - 0.7) * 0.8)
        coherence_hint = _clamp01(0.9 - abs(balance - 0.7) * 0.9)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={"profile": {"balance": balance}},
            )
        )
        stability = _clamp01(1.0 - (se.risk + se.uncertainty) / 2.0)
        explain = f"bal={balance:.2f} kurt={kurt:.2f} poc={poc_price:.2f}"
        return ProfileMetrics(
            poc=poc_price,
            vah=vah,
            val=val,
            kurtosis=kurt,
            balance=balance,
            stability=stability,
            se41=se,
            explain=explain,
        )

    def snapshot_dict(self) -> Dict[str, Any]:
        m = self.metrics()
        return {
            "poc": m.poc,
            "vah": m.vah,
            "val": m.val,
            "kurtosis": m.kurtosis,
            "balance": m.balance,
            "stability": m.stability,
            "se41": {
                "risk": m.se41.risk,
                "uncertainty": m.se41.uncertainty,
                "coherence": m.se41.coherence,
            },
            "explain": m.explain,
        }


def _selftest() -> int:  # pragma: no cover
    mp = MarketProfile()
    mp.simulate_random(500)
    s = mp.snapshot_dict()
    assert "poc" in s
    print("MarketProfile selftest", s["balance"])
    return 0


__all__ = ["MarketProfile", "ProfileMetrics"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    mp = MarketProfile()
    mp.simulate_random(300)
    print(json.dumps(mp.snapshot_dict(), indent=2))
