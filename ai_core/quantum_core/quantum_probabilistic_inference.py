from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence
import math

from ai_core.probabilistic_rendering_engine import (
    ProbabilityField,
    StrategyWeight,
    clamp01,
)

try:  # pragma: no cover - optional entropy helper
    from symbolic_core.se41_ext import ouroboros_score as _se41_ouroboros_score
except Exception:  # pragma: no cover - development fallback

    def _se41_ouroboros_score(metrics: Dict[str, float]) -> float:
        if not metrics:
            return 0.0
        values = [float(v) for v in metrics.values()]
        return clamp01(sum(values) / max(1, len(values)))


@dataclass
class InferenceReport:
    refined_field: List[List[float]]
    hotspots: List[Dict[str, float]]
    adjustments: List[StrategyWeight]
    summary: Dict[str, float]


def refine_field(field: ProbabilityField, *, focus: float = 0.65) -> List[List[float]]:
    """Return a softened + sharpened copy of the probability grid."""

    nx, ny = field.nx, field.ny
    grid = field.grid
    out: List[List[float]] = []
    for y in range(ny):
        row: List[float] = []
        for x in range(nx):
            center = grid[y][x]
            acc = center * (1.0 + focus)
            weight = 1.0 + focus
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx_idx = x + dx
                    ny_idx = y + dy
                    if 0 <= nx_idx < nx and 0 <= ny_idx < ny:
                        w = 1.0 if dx == 0 or dy == 0 else 0.5
                        acc += grid[ny_idx][nx_idx] * w
                        weight += w
            value = clamp01(acc / max(weight, 1e-6))
            row.append(value)
        total = sum(row) or 1.0
        row = [val / total for val in row]
        out.append(row)
    return out


def find_hotspots(grid: List[List[float]], *, count: int = 4) -> List[Dict[str, float]]:
    flat: List[Dict[str, float]] = []
    for y, row in enumerate(grid):
        for x, value in enumerate(row):
            flat.append({"x": float(x), "y": float(y), "value": float(value)})
    flat.sort(key=lambda item: item["value"], reverse=True)
    return flat[: max(0, count)]


def adjust_strategies(
    strategies: Sequence[StrategyWeight],
    *,
    conservatism: float,
    ethos_bias: float,
) -> List[StrategyWeight]:
    conservatism = clamp01(conservatism)
    ethos_bias = clamp01(ethos_bias)
    raw: List[float] = []
    names: List[str] = []
    for strategy in strategies:
        boost = 1.0
        if "hedge" in strategy.name:
            boost += 0.35 * conservatism
        if "momentum" in strategy.name:
            boost += 0.20 * (1.0 - conservatism)
        if "quantum" in strategy.name:
            boost += 0.25 * ethos_bias
        raw.append(clamp01(strategy.weight * boost))
        names.append(strategy.name)
    total = sum(raw) or 1.0
    return [StrategyWeight(name, value / total) for name, value in zip(names, raw)]


def entropy(grid: List[List[float]]) -> float:
    eps = 1e-9
    h = 0.0
    for row in grid:
        for value in row:
            v = clamp01(value)
            if v <= eps:
                continue
            h -= v * math.log(v + eps, 2)
    return float(h)


def summarize_field(
    field: ProbabilityField,
    refined: List[List[float]],
) -> Dict[str, Any]:
    flat_values = [val for row in refined for val in row]
    peak = max(flat_values) if flat_values else 0.0
    mean = sum(flat_values) / max(1, len(flat_values))
    std = math.sqrt(
        sum((value - mean) ** 2 for value in flat_values) / max(1, len(flat_values))
    )
    entropy_val = entropy(refined)
    max_entropy = math.log(max(1, len(flat_values)), 2) if flat_values else 1.0
    entropy_norm = entropy_val / max_entropy if max_entropy > 0 else 0.0
    metrics = {
        "waste": clamp01((1.0 - peak) * (1.0 - mean)),
        "oscillation": clamp01(std * 1.5),
        "stasis": clamp01(1.0 - entropy_norm),
        "novelty": clamp01(entropy_norm),
    }
    score = _se41_ouroboros_score(metrics)
    return {
        "entropy": entropy_val,
        "peak": peak,
        "mean": mean,
        "std": std,
        "ouroboros_score": score,
        "ouroboros_metrics": metrics,
        "ts": field.ts,
    }


def run_inference(
    field: ProbabilityField,
    strategies: Sequence[StrategyWeight],
    *,
    conservatism: float,
    ethos_bias: float,
) -> InferenceReport:
    refined = refine_field(field, focus=0.55 + 0.35 * conservatism)
    hotspots = find_hotspots(refined, count=5)
    adjustments = adjust_strategies(strategies, conservatism=conservatism, ethos_bias=ethos_bias)
    summary = summarize_field(field, refined)
    report = InferenceReport(
        refined_field=refined,
        hotspots=hotspots,
        adjustments=adjustments,
        summary=summary,
    )
    return report


__all__ = [
    "InferenceReport",
    "adjust_strategies",
    "entropy",
    "find_hotspots",
    "refine_field",
    "run_inference",
    "summarize_field",
]
