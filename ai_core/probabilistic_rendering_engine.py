from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import math
import random

try:
    from symbolic_core.se41_ext import clamp01 as _se41_clamp01
    from symbolic_core.se41_ext import ethos_avg as _se41_ethos_avg

    def clamp01(value: float) -> float:
        return float(_se41_clamp01(value))

    def ethos_avg(values: Dict[str, float]) -> float:
        return float(_se41_ethos_avg(values))

except Exception:  # pragma: no cover - development fallback

    def clamp01(value: float) -> float:
        try:
            numeric = float(value)
        except Exception:
            return 0.0
        if numeric < 0.0:
            return 0.0
        if numeric > 1.0:
            return 1.0
        return numeric

    def ethos_avg(values: Dict[str, float]) -> float:
        if not values:
            return 0.0
        seq = [float(v) for v in values.values()]
        return clamp01(sum(seq) / max(1, len(seq)))

try:
    from utils.audit import audit_ndjson as _audit
except Exception:  # pragma: no cover - development fallback

    def _audit(event: str, **payload: Any) -> None:
        return None


def _now() -> float:
    import time

    return time.time()


@dataclass
class ProbabilityField:
    nx: int
    ny: int
    grid: List[List[float]]
    params: Dict[str, float]
    ts: float


@dataclass
class StrategyWeight:
    name: str
    weight: float


@dataclass
class RenderRequest:
    signals: Dict[str, Any]
    features: Optional[Dict[str, float]] = None
    nx: int = 32
    ny: int = 32
    sharpness: float = 0.6
    noise: float = 0.1
    seed: Optional[int] = None


@dataclass
class RenderResponse:
    field: ProbabilityField
    strategies: List[StrategyWeight]
    rec: str


class ProbabilisticRenderingEngine:
    """Sovereign-aligned, simulation-only probability renderer."""

    def __init__(self, name: str = "PQRE") -> None:
        self.name = name

    def render(self, req: RenderRequest) -> RenderResponse:
        signals = self._sanitize(req.signals)
        rnd = random.Random(req.seed if req.seed is not None else 7)

        smoothness, sharpness, noise, ethos = self._params_from_se41(signals, req.sharpness, req.noise)
        grid = self._make_field(req.nx, req.ny, smoothness, sharpness, noise, ethos, rnd)
        strategies = self._strategy_weights(signals, rnd)
        recommendation = self._recommend(signals, sharpness, noise, strategies)

        field = ProbabilityField(
            nx=req.nx,
            ny=req.ny,
            grid=grid,
            params={
                "smoothness": smoothness,
                "sharpness": sharpness,
                "noise": noise,
                "ethos_avg": ethos,
            },
            ts=_now(),
        )

        _audit(
            "pqre_render",
            signals=signals,
            features=req.features or {},
            params=field.params,
            strategies=[asdict(strategy) for strategy in strategies],
        )

        return RenderResponse(field=field, strategies=strategies, rec=recommendation)

    def _sanitize(self, raw: Dict[str, Any]) -> Dict[str, float]:
        return {
            "coherence": clamp01(raw.get("coherence", 0.0)),
            "impetus": clamp01(raw.get("impetus", 0.0)),
            "risk": clamp01(raw.get("risk", 1.0)),
            "uncertainty": clamp01(raw.get("uncertainty", 1.0)),
            "mirror": clamp01(raw.get("mirror_consistency", 0.0)),
            "S_EM": clamp01(raw.get("S_EM", 0.0)),
            "ethos": ethos_avg(raw.get("ethos") or {}),
        }

    def _params_from_se41(self, signals: Dict[str, float], sharpness: float, noise: float) -> List[float]:
        smoothness = clamp01(0.55 * signals["coherence"] + 0.25 * signals["mirror"] + 0.20 * (1.0 - signals["uncertainty"]))
        sharp = clamp01(0.65 * sharpness + 0.25 * signals["impetus"] + 0.10 * signals["S_EM"])
        noise_eff = clamp01(0.6 * noise + 0.4 * (0.6 * signals["risk"] + 0.4 * signals["uncertainty"]))
        return [smoothness, sharp, noise_eff, signals["ethos"]]

    def _make_field(
        self,
        nx: int,
        ny: int,
        smoothness: float,
        sharpness: float,
        noise: float,
        ethos: float,
        rnd: random.Random,
    ) -> List[List[float]]:
        xs = [(i - (nx - 1) / 2) / max(1, (nx - 1)) for i in range(nx)]
        ys = [(j - (ny - 1) / 2) / max(1, (ny - 1)) for j in range(ny)]
        k = 1.0 - 0.6 * smoothness
        base_sigma = max(0.08, 0.28 * (1.0 - sharpness))
        grid: List[List[float]] = []
        for y in ys:
            row: List[float] = []
            for x in xs:
                radius_sq = x * x + y * y
                peak = math.exp(-radius_sq / (2.0 * base_sigma * base_sigma))
                ring = 0.5 + 0.5 * math.cos(2.0 * math.pi * (k * x + k * y))
                value = clamp01(0.55 * peak + 0.35 * ring + 0.10 * ethos)
                if noise > 0:
                    value = clamp01(value + (rnd.random() - 0.5) * 0.15 * noise)
                row.append(value)
            total = sum(row) or 1.0
            row = [val / total for val in row]
            grid.append(row)
        return grid

    def _strategy_weights(self, signals: Dict[str, float], rnd: random.Random) -> List[StrategyWeight]:
        names = [
            "classical_core",
            "quantum_probe",
            "rl_adapt",
            "hedge_guard",
            "momentum",
        ]
        raw = [
            clamp01(
                0.40 * signals["coherence"]
                + 0.20 * (1.0 - signals["risk"])
                + 0.10 * signals["mirror"]
                + 0.05 * signals["S_EM"]
                + 0.25 * signals["ethos"]
            ),
            clamp01(
                0.30 * signals["impetus"]
                + 0.25 * (1.0 - signals["uncertainty"])
                + 0.20 * signals["mirror"]
                + 0.15 * signals["S_EM"]
                + 0.10 * signals["ethos"]
            ),
            clamp01(
                0.25 * signals["impetus"]
                + 0.25 * (1.0 - signals["risk"])
                + 0.25 * (1.0 - signals["uncertainty"])
                + 0.15 * signals["coherence"]
                + 0.10 * signals["ethos"]
            ),
            clamp01(
                0.35 * (1.0 - signals["risk"])
                + 0.25 * (1.0 - signals["uncertainty"])
                + 0.20 * signals["coherence"]
                + 0.10 * signals["S_EM"]
                + 0.10 * signals["ethos"]
            ),
            clamp01(
                0.30 * signals["impetus"]
                + 0.20 * signals["coherence"]
                + 0.20 * signals["mirror"]
                + 0.20 * (1.0 - signals["risk"])
                + 0.10 * signals["ethos"]
            ),
        ]
        raw = [clamp01(value + (rnd.random() - 0.5) * 0.02) for value in raw]
        total = sum(raw) or 1.0
        return [StrategyWeight(name, value / total) for name, value in zip(names, raw)]

    def _recommend(
        self,
        signals: Dict[str, float],
        sharpness: float,
        noise: float,
        strategies: List[StrategyWeight],
    ) -> str:
        if signals["risk"] >= 0.35 or signals["uncertainty"] >= 0.45:
            return (
                "Elevated risk/uncertainty: limit live exposure, prefer paper runs and hedged ensembles; "
                "tighten caps and reassess after a short window."
            )
        if sharpness >= 0.65 and signals["coherence"] >= 0.75 and signals["impetus"] >= 0.45:
            leader = max(strategies, key=lambda item: item.weight).name
            return (
                "Favorable shape: prepare bounded execution; lead strategy = "
                f"{leader} (superposition retained until act)."
            )
        return "Neutral shape: continue observation and small-paper bursts; refine weights with feedback."


__all__ = [
    "ProbabilisticRenderingEngine",
    "RenderRequest",
    "RenderResponse",
    "ProbabilityField",
    "StrategyWeight",
]
