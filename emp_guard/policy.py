from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any, Dict, Mapping

DEFAULT_POSTURE: Dict[str, Any] = {
    "exposure": {"E1": "medium", "E2": "medium", "E3": "low"},
    "hardening": {
        "surge_filters": "present",
        "grounding_review": "due",
        "line_conditioners": "present",
        "storage_replication": "healthy",
    },
    "drills": {"last_run": "never", "recommended_interval_days": 30},
    "caps": {"cost_usd_max": 2000, "hours_max": 4, "energy_kwh_max": 500},
}

_POSTURE: Dict[str, Any] = deepcopy(DEFAULT_POSTURE)
_LOCK = Lock()


def _snapshot() -> Dict[str, Any]:
    return deepcopy(_POSTURE)


def get_posture() -> Dict[str, Any]:
    """Return a deep copy of the current posture state."""
    with _LOCK:
        return _snapshot()


def reset_posture() -> Dict[str, Any]:
    """Restore posture to defaults (mainly for tests)."""
    with _LOCK:
        _POSTURE.clear()
        _POSTURE.update(deepcopy(DEFAULT_POSTURE))
        return _snapshot()


def update_caps(caps: Mapping[str, Any]) -> Dict[str, Any]:
    """Merge caps fields and return the updated caps snapshot."""
    filtered = {k: v for k, v in caps.items() if v is not None}
    if not filtered:
        with _LOCK:
            return deepcopy(_POSTURE.get("caps", {}))

    with _LOCK:
        current_caps = _POSTURE.setdefault("caps", {})
        current_caps.update(filtered)
        return deepcopy(current_caps)
