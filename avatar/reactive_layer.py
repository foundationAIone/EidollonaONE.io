from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple

from ai_core.probabilistic_rendering_engine import ProbabilisticRenderingEngine, RenderRequest


@dataclass
class ReactiveDirective:
    mood: str
    pose: str
    animation: str
    recommendation: str
    strategies: List[Dict[str, Any]]
    field: Dict[str, Any]
    updated_at: float

    def as_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


_ENGINE = ProbabilisticRenderingEngine(name="PQRE-Avatar")
_CACHE_LOCK = RLock()
_LAST_CACHE: Dict[str, Any] = {"directive": None, "ts": 0.0, "signals_hash": None}


def _hash_signals(signals: Dict[str, Any], features: Optional[Dict[str, float]]) -> Tuple:
    features_items: Tuple = tuple(sorted((features or {}).items()))
    signals_items: Tuple = tuple(sorted(signals.items()))
    return (signals_items, features_items)


def _choose_mood(params: Dict[str, float]) -> str:
    sharpness = params.get("sharpness", 0.0)
    noise = params.get("noise", 0.0)
    smoothness = params.get("smoothness", 0.0)
    if sharpness >= 0.72 and noise <= 0.25:
        return "focused"
    if smoothness >= 0.65 and noise <= 0.35:
        return "composed"
    if noise >= 0.45:
        return "alert"
    return "reflective"


def _choose_pose(mood: str, strategies: List[Dict[str, Any]]) -> str:
    if not strategies:
        return "neutral"
    primary = max(strategies, key=lambda item: item.get("weight", 0.0))
    name = primary.get("name", "core")
    if mood == "focused":
        return f"focus_{name}"
    if mood == "alert":
        return f"sentinel_{name}"
    if mood == "composed":
        return f"grace_{name}"
    return f"reflect_{name}"


def _choose_animation(mood: str, params: Dict[str, float]) -> str:
    amplitude = params.get("noise", 0.0)
    if mood == "alert":
        return "scan_environment"
    if mood == "focused" and amplitude < 0.35:
        return "micro_gesture"
    if mood == "composed":
        return "gentle_nod"
    return "idle_breathe"


def _normalize_field(field: Dict[str, Any]) -> Dict[str, Any]:
    grid = field.get("grid", [])
    if not grid or not isinstance(grid, list):
        return {**field, "grid": []}
    width = len(grid[0]) if grid and isinstance(grid[0], list) else 0
    total = 0.0
    for row in grid:
        total += sum(float(v) for v in row)
    if total <= 0 or width == 0:
        return {**field, "grid": grid}
    coef = len(grid) * width / total
    normalized = [[float(v) * coef for v in row] for row in grid]
    return {**field, "grid": normalized}


def generate_directive(
    *,
    signals: Dict[str, Any],
    features: Optional[Dict[str, float]] = None,
    seed: Optional[int] = None,
    cache_seconds: float = 1.2,
) -> ReactiveDirective:
    key = _hash_signals(signals, features)
    now = time.time()
    with _CACHE_LOCK:
        cached = _LAST_CACHE.get("directive")
        cached_hash = _LAST_CACHE.get("signals_hash")
        cached_ts = float(_LAST_CACHE.get("ts") or 0.0)
        if cached and cached_hash == key and (now - cached_ts) <= cache_seconds:
            return cached

    req = RenderRequest(signals=signals, features=features, seed=seed or int(now) % 1000)
    response = _ENGINE.render(req)
    params = response.field.params
    mood = _choose_mood(params)
    pose = _choose_pose(mood, [asdict(s) for s in response.strategies])
    animation = _choose_animation(mood, params)
    directive = ReactiveDirective(
        mood=mood,
        pose=pose,
        animation=animation,
        recommendation=response.rec,
        strategies=[asdict(s) for s in response.strategies],
        field={**_normalize_field(asdict(response.field))},
        updated_at=now,
    )

    with _CACHE_LOCK:
        _LAST_CACHE["directive"] = directive
        _LAST_CACHE["ts"] = now
        _LAST_CACHE["signals_hash"] = key

    return directive


def directive_summary(directive: ReactiveDirective) -> Dict[str, Any]:
    moves = {
        "pose": directive.pose,
        "animation": directive.animation,
        "mood": directive.mood,
        "recommendation": directive.recommendation,
    }
    stats = {
        "strategy_count": len(directive.strategies),
        "max_weight": max((float(s.get("weight", 0.0)) for s in directive.strategies), default=0.0),
    }
    return {
        "updated_at": directive.updated_at,
        "moves": moves,
        "stats": stats,
    }
