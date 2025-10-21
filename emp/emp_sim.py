from __future__ import annotations

from typing import Any, Dict, Optional

from .emp_core import grid


def step(state: Dict[str, Any], se41: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    t = float(state.get("t", 0.0)) + 0.1
    nx = int(state.get("nx", 32))
    ny = int(state.get("ny", 32))
    base_signals = dict(state.get("signals") or {})
    signals = dict(se41 or base_signals)
    result = grid(nx, ny, t, signals)
    result["signals"] = signals
    if se41 is not None:
        result["se41"] = dict(se41)
        result["source_signals"] = base_signals
    else:
        result["source_signals"] = signals
    return result
