"""Feature flag helpers for optional subsystems."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Mapping, Optional

__all__ = ["quantum_config"]


_DEFAULT_QUANTUM_FLAGS: Dict[str, Any] = {
    "feature_enabled": False,
    "provider": "sim",
    "max_qubits": 40,
    "max_cost_cents": 200,
    "max_latency_sec": 300,
    "redact_payload": True,
}


def quantum_config(overrides: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Return quantum feature flag configuration.

    Configuration can be overridden via the `EIDOLLONA_QUANTUM_FLAGS` environment
    variable (JSON encoded) or by passing an overrides mapping.
    """

    cfg = dict(_DEFAULT_QUANTUM_FLAGS)
    env_payload = os.getenv("EIDOLLONA_QUANTUM_FLAGS")
    if env_payload:
        try:
            cfg.update(json.loads(env_payload))
        except Exception:
            pass
    if overrides:
        for key, value in overrides.items():
            cfg[key] = value
    return cfg
