"""SAFE-first priority 9 status helper.

Provides deterministic placeholder telemetry so symbolic components can keep
reporting the same structure even when the full reality manipulation stack is
not available in the development environment.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict

_DEFAULT_STATUS: Dict[str, Any] = {
    "priority": 9,
    "status": "offline",
    "timestamp": 0.0,
    "metrics": {
        "reality_manipulation_level": 0.0,
        "dimensional_transcendence_level": 0.0,
        "physical_world_control_level": 0.0,
        "consciousness_reality_unity": 0.0,
    },
    "advisories": [
        "Reality manipulation core unavailable; operating in SAFE placeholder mode.",
    ],
}


def _stable_seed() -> float:
    env_value = os.getenv("REALITY_PRIORITY9_SEED")
    if env_value is None:
        return float(int(time.time()))
    try:
        return float(env_value)
    except ValueError:
        return float(int.from_bytes(env_value.encode("utf-8"), "big") % 10_000)


def get_priority_9_status(force_refresh: bool = False) -> Dict[str, Any]:
    """Return a deterministic SAFE placeholder status document.

    Parameters
    ----------
    force_refresh:
        Ignored in the placeholder implementation. Present for API parity.
    """

    base = dict(_DEFAULT_STATUS)
    metrics = dict(base["metrics"])
    seed = _stable_seed()
    # Map seed into soft activity ranges so dashboards stay lively but SAFE.
    metrics.update(
        reality_manipulation_level=min(0.3, (seed % 37) / 123.0),
        dimensional_transcendence_level=min(0.25, (seed % 23) / 111.0),
        physical_world_control_level=0.0,
        consciousness_reality_unity=min(0.4, (seed % 41) / 101.0),
    )
    base.update(timestamp=time.time(), metrics=metrics)
    return base


__all__ = ["get_priority_9_status"]
