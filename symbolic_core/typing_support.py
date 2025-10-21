"""Typing helpers shared across the symbolic core.

This module deliberately avoids importing the heavy symbolic implementation to
prevent circular dependencies. It provides a light `TypedDict` for the common
symbolic outputs and small utilities that normalize results into plain dicts.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, TypedDict


def _clip01(x: float) -> float:
    """Clamp a float into [0, 1] without raising."""
    try:
        xf = float(x)
    except Exception:
        return 0.0
    return 0.0 if xf < 0.0 else 1.0 if xf > 1.0 else xf


class SymbolicMetrics(TypedDict, total=False):
    """Lightweight structure describing symbolic evaluation outputs."""

    confidence: float
    resonance: float
    details: Dict[str, Any]


def is_symbolic_metrics(value: Any) -> bool:
    """Best-effort runtime check that `value` looks like SymbolicMetrics."""

    if isinstance(value, Mapping):
        keys = value.keys()
        return any(key in keys for key in ("confidence", "resonance", "details"))
    return any(hasattr(value, key) for key in ("confidence", "resonance", "details"))


def metrics_to_dict(value: Any) -> Dict[str, Any]:
    """Normalize a symbolic evaluation result into a plain `dict`."""

    out: Dict[str, Any] = {"confidence": 0.5, "resonance": 0.5, "details": {}}

    if value is None:
        return out

    if isinstance(value, Mapping):
        conf = value.get("confidence", out["confidence"])
        res = value.get("resonance", out["resonance"])
        det = value.get("details", out["details"])
        out["confidence"] = _clip01(conf)  # type: ignore[arg-type]
        out["resonance"] = _clip01(res)  # type: ignore[arg-type]
        out["details"] = dict(det) if isinstance(det, Mapping) else out["details"]
        for key, val in value.items():
            if key not in out:
                out[key] = val
        return out

    try:
        conf = getattr(value, "confidence", out["confidence"])
        res = getattr(value, "resonance", out["resonance"])
        det = getattr(value, "details", out["details"])
        out["confidence"] = _clip01(conf)
        out["resonance"] = _clip01(res)
        out["details"] = dict(det) if isinstance(det, Mapping) else out["details"]
    except Exception:
        return out

    return out


__all__ = ["SymbolicMetrics", "is_symbolic_metrics", "metrics_to_dict"]
