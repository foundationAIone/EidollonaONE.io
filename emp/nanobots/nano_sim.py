from __future__ import annotations

from typing import Any, Dict, Optional

from ..emp_core import grid


def init_field(nx: int = 32, ny: int = 32, signals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"nx": int(nx), "ny": int(ny), "t": 0.0, "signals": dict(signals or {})}


def step_field(state: Dict[str, Any]) -> Dict[str, Any]:
    t = float(state.get("t", 0.0)) + 0.05
    nx = int(state.get("nx", 32))
    ny = int(state.get("ny", 32))
    signals = dict(state.get("signals") or {})
    result = grid(nx, ny, t, signals)
    result["signals"] = signals
    return result
