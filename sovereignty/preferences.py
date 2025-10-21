from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional

_PREFS_PATH = Path(os.getenv("SOVEREIGN_PREFS_PATH", "sovereignty_data/preferences.json")).resolve()
_PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)

_ALLOWED_KEYS = {
    "coherence_min": (0.0, 1.0),
    "impetus_min": (0.0, 1.0),
    "risk_max": (0.0, 1.0),
    "uncertainty_max": (0.0, 1.0),
    "ethos_floor": (0.0, 1.0),
    "strategy_bias": (-1.0, 1.0),
    "notes": None,
}


@dataclass
class SovereignPreferences:
    coherence_min: float = 0.78
    impetus_min: float = 0.52
    risk_max: float = 0.28
    uncertainty_max: float = 0.42
    ethos_floor: float = 0.70
    strategy_bias: float = 0.0
    notes: str = ""
    updated_at: float = 0.0
    updated_by: str = "system"

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


_PREFS_LOCK = RLock()


def _load_from_disk() -> Optional[Dict[str, Any]]:
    if not _PREFS_PATH.exists():
        return None
    try:
        text = _PREFS_PATH.read_text(encoding="utf-8")
        return json.loads(text)
    except Exception:
        return None


def _save_to_disk(payload: Dict[str, Any]) -> None:
    try:
        _PREFS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # best-effort; swallow IO errors to keep SAFE mode resilient
        pass


def _validate_update(data: Dict[str, Any]) -> Dict[str, Any]:
    validated: Dict[str, Any] = {}
    for key, value in data.items():
        if key not in _ALLOWED_KEYS:
            continue
        bounds = _ALLOWED_KEYS[key]
        if bounds is None:
            validated[key] = str(value)
            continue
        lo, hi = bounds
        try:
            numeric = float(value)
        except Exception:
            continue
        numeric = max(lo, min(hi, numeric))
        validated[key] = numeric
    return validated


def _hydrate(default_actor: str = "system") -> SovereignPreferences:
    raw = _load_from_disk()
    prefs = SovereignPreferences(updated_at=time.time(), updated_by=default_actor)
    if not raw:
        return prefs

    payload = {**prefs.as_dict(), **raw}
    try:
        prefs = SovereignPreferences(**payload)
    except TypeError:
        # Fallback if stored payload has legacy keys
        prefs = SovereignPreferences()
        for key, value in payload.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)
    return prefs


def get_preferences() -> Dict[str, Any]:
    with _PREFS_LOCK:
        return _hydrate().as_dict()


def update_preferences(update: Dict[str, Any], actor: str = "system") -> Dict[str, Any]:
    if not isinstance(update, dict):
        raise ValueError("update must be a dict")
    cleaned = _validate_update(update)
    if not cleaned:
        raise ValueError("no valid preference keys provided")

    with _PREFS_LOCK:
        prefs = _hydrate(default_actor=actor)
        for key, value in cleaned.items():
            setattr(prefs, key, value)
        prefs.updated_at = time.time()
        prefs.updated_by = actor
        payload = prefs.as_dict()
        _save_to_disk(payload)
        return payload


def reset_preferences(actor: str = "system") -> Dict[str, Any]:
    with _PREFS_LOCK:
        prefs = SovereignPreferences(updated_at=time.time(), updated_by=actor)
        payload = prefs.as_dict()
        _save_to_disk(payload)
        return payload