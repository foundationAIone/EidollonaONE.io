from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

from .se41_adapter import se41_resilience, se41_to_field_params


def _field_at(
    x: float,
    y: float,
    t: float,
    params: Dict[str, float],
) -> Tuple[float, float, float]:
    amplitude = params.get("amplitude", 0.0)
    smoothness = params.get("smoothness", 0.0)
    noise = params.get("noise", 0.0)
    ethos_bias = params.get("ethos_avg", 0.0) - 0.5

    phase = t * (0.5 + 0.4 * smoothness)
    freq_x = 0.7 - 0.25 * smoothness
    freq_y = 0.6 - 0.2 * smoothness
    cross_freq = 0.3 + 0.2 * smoothness

    base_ex = math.sin(x * freq_x + phase) * math.cos(y * freq_y - 0.6 * phase)
    base_ey = math.cos(x * 0.4 - 0.3 * phase) * math.sin(y * (0.9 + 0.3 * smoothness) + 0.4 * phase)
    base_ez = math.sin((x + y) * cross_freq + 0.7 * phase)

    jitter = math.sin(13.0 * x + 17.0 * y + 19.0 * t) * (0.1 * noise)

    ex = amplitude * base_ex + jitter
    ey = amplitude * base_ey + 0.5 * jitter
    ez = 0.25 * amplitude * base_ez + 0.3 * jitter

    bias = 0.2 * ethos_bias
    return (ex + bias, ey + bias, ez + 0.5 * bias)


def grid(nx: int, ny: int, t: float = 0.0, signals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    nx = max(1, int(nx))
    ny = max(1, int(ny))
    t = float(t)

    signals = signals or {}
    params = se41_to_field_params(signals)
    resilience = se41_resilience(signals)

    xs = [(i - (nx - 1) / 2) / 10.0 for i in range(nx)]
    ys = [(j - (ny - 1) / 2) / 10.0 for j in range(ny)]
    field = [[_field_at(x, y, t, params) for x in xs] for y in ys]

    return {
        "nx": nx,
        "ny": ny,
        "t": t,
        "E": field,
        "resilience": resilience,
        "params": params,
    }
