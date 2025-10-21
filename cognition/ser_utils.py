"""Utilities for reading Self Evidence Records (SER)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Tuple

_DEFAULT_PATH = Path("consciousness_data/ser.log.jsonl")


def _parse_line(raw: str) -> Tuple[float, str] | None:
    try:
        data = json.loads(raw)
        ser = data.get("ser", {})
        score = float(ser.get("score", 0.0))
        ts_raw = data.get("ts")
        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                return score, ts.isoformat()
            except ValueError:
                return score, ts_raw
        return score, ""
    except Exception:
        return None


def read_last_ser(path: str | None = None) -> Tuple[float, str]:
    """Return the most recent SER score and timestamp.

    The function is resilient to missing files and malformed rows, returning
    `(0.0, "")` when no entries are available.
    """

    ser_path = Path(path) if path else _DEFAULT_PATH
    if not ser_path.exists():
        return 0.0, ""

    score = 0.0
    timestamp = ""
    try:
        for raw in ser_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            parsed = _parse_line(raw)
            if parsed is not None:
                score, timestamp = parsed
    except Exception:
        return 0.0, ""
    return score, timestamp


__all__ = ["read_last_ser"]
