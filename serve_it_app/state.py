from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
STATE_PATH = LOG_DIR / "serveit_state.json"
_LOCK = threading.Lock()


def _default_state() -> Dict[str, List[Dict[str, object]]]:
    return {
        "users": [],
        "providers": [],
        "hoas": [],
        "service_types": [],
        "requests": [],
        "quotes": [],
        "bookings": [],
        "payments": [],
        "ratings": [],
        "affiliates": [],
    }


def _ensure_dirs() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)


def load_state() -> Dict[str, List[Dict[str, object]]]:
    _ensure_dirs()
    if not STATE_PATH.exists():
        return _default_state()
    try:
        with STATE_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return _default_state()


def save_state(state: Dict[str, List[Dict[str, object]]]) -> None:
    _ensure_dirs()
    with STATE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)

@contextmanager
def mutate_state() -> Iterator[Dict[str, List[Dict[str, object]]]]:
    with _LOCK:
        state = load_state()
        try:
            yield state
        finally:
            save_state(state)
