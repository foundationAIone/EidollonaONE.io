from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional

from ..se41_adapter import se41_resilience, se41_to_field_params


def init_swarm(n: int = 32, seed: int = 7, signals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    random.seed(seed)
    count = max(1, int(n))
    points = [(random.uniform(-1, 1), random.uniform(-1, 1)) for _ in range(count)]
    return {
        "t": 0.0,
        "agents": [{"x": x, "y": y} for (x, y) in points],
        "signals": dict(signals or {}),
    }


def step_swarm(state: Dict[str, Any]) -> Dict[str, Any]:
    agents = state.get("agents", [])
    t = float(state.get("t", 0.0)) + 0.1
    signals = dict(state.get("signals") or {})
    params = se41_to_field_params(signals)
    resilience = se41_resilience(signals)

    smoothness = params.get("smoothness", 0.0)
    amplitude = params.get("amplitude", 0.0)
    noise = params.get("noise", 0.0)

    base_speed = 0.01 + 0.03 * amplitude
    orbit_gain = 1.0 + 0.6 * smoothness
    center_pull = 0.02 + 0.08 * resilience
    jitter_scale = 0.005 * noise

    out: List[Dict[str, float]] = []
    for idx, agent in enumerate(agents):
        x = float(agent.get("x", 0.0))
        y = float(agent.get("y", 0.0))

        spiral = 3.0 + 1.2 * smoothness
        vx = base_speed * math.sin(spiral * y + orbit_gain * t)
        vy = base_speed * math.cos(spiral * x - orbit_gain * t)

        cx = -center_pull * x
        cy = -center_pull * y

        jitter = jitter_scale * math.sin(11.0 * idx + 5.0 * x + 7.0 * y + t)

        out.append({"x": x + vx + cx + jitter, "y": y + vy + cy - jitter})

    return {
        "t": t,
        "agents": out,
        "signals": signals,
        "telemetry": {"params": params, "resilience": resilience},
    }
