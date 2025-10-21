"""SAFE-first symbolic priority 10 status helper."""

from __future__ import annotations

import os
import random
import time
from typing import Any, Dict

_DEFAULT_STATUS: Dict[str, Any] = {
    "priority": 10,
    "status": "offline",
    "timestamp": 0.0,
    "metrics": {
        "priority_10_effectiveness": 0.0,
        "signal_alignment": 0.0,
        "symbolic_density": 0.0,
    },
    "advisories": [
        "Priority 10 interface operating in SAFE placeholder mode.",
    ],
}


def _rng() -> random.Random:
    seed_env = os.getenv("SYMBOLIC_PRIORITY10_SEED")
    if seed_env is None:
        seed = int(time.time())
    else:
        try:
            seed = int(seed_env)
        except ValueError:
            seed = int.from_bytes(seed_env.encode("utf-8"), "big") % 1_000_000
    return random.Random(seed)


def get_priority_10_status(force_refresh: bool = False) -> Dict[str, Any]:
    """Return SAFE placeholder telemetry for symbolic priority 10 channel."""

    rng = _rng()
    metrics = dict(_DEFAULT_STATUS["metrics"])
    metrics.update(
        priority_10_effectiveness=round(rng.uniform(0.2, 0.45), 3),
        signal_alignment=round(rng.uniform(0.3, 0.55), 3),
        symbolic_density=round(rng.uniform(0.25, 0.5), 3),
    )
    return {
        **_DEFAULT_STATUS,
        "status": "placeholder",
        "timestamp": time.time(),
        "metrics": metrics,
    }


__all__ = ["get_priority_10_status"]
