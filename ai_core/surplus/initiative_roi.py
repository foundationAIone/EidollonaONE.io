"""Initiative ROI Tracker (SE41)

What
----
Tracks funding efficiency for initiatives supported by treasury allocations.
Computes governance-adjusted ROI incorporating stability (coherence - risk).

Why
---
1. Enables capital rebalancing toward resilient, coherent value creators.
2. Down-ranks volatile / uncertain initiatives despite raw ROI.
3. Supplies allocator with historical performance context.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class InitiativeRecord:
    name: str
    invested: float
    returns: float
    risk: float
    uncertainty: float
    coherence: float

    @property
    def raw_roi(self) -> float:
        return (self.returns - self.invested) / self.invested if self.invested else 0.0

    @property
    def stability(self) -> float:
        return max(0.0, 1 - (self.risk + self.uncertainty) / 2)

    @property
    def adjusted_roi(self) -> float:
        return self.raw_roi * (0.6 * self.stability + 0.4 * self.coherence)


class InitiativeROITracker:
    def __init__(self) -> None:
        self.records: Dict[str, InitiativeRecord] = {}

    def update(
        self,
        name: str,
        invested_delta: float,
        returns_delta: float,
        risk: float,
        uncertainty: float,
        coherence: float,
    ) -> None:
        r = self.records.get(name)
        if r is None:
            r = InitiativeRecord(
                name, invested_delta, returns_delta, risk, uncertainty, coherence
            )
        else:
            r.invested += invested_delta
            r.returns += returns_delta
            # blend risk metrics (EWMA style)
            r.risk = 0.7 * r.risk + 0.3 * risk
            r.uncertainty = 0.7 * r.uncertainty + 0.3 * uncertainty
            r.coherence = 0.7 * r.coherence + 0.3 * coherence
        self.records[name] = r

    def leaderboard(self, top: int = 5) -> List[Dict[str, Any]]:
        ranked = sorted(
            self.records.values(), key=lambda r: r.adjusted_roi, reverse=True
        )[:top]
        return [
            {
                "name": r.name,
                "raw_roi": round(r.raw_roi, 4),
                "adj_roi": round(r.adjusted_roi, 4),
                "stability": round(r.stability, 3),
            }
            for r in ranked
        ]


__all__ = ["InitiativeROITracker", "InitiativeRecord"]


def _selftest() -> int:  # pragma: no cover
    tr = InitiativeROITracker()
    tr.update("R&D_AI", 100, 130, 0.3, 0.25, 0.85)
    tr.update("Ops_Automation", 80, 90, 0.25, 0.2, 0.8)
    lb = tr.leaderboard()
    assert lb
    print("InitiativeROITracker selftest", lb[0])
    return 0


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(_selftest())
