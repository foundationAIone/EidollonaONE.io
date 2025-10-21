"""Symbolic asset manifest for consolidated web_interface server."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import json

try:
    from symbolic_core.symbolic_equation import SymbolicEquation41
except Exception:  # pragma: no cover - fallback if symbolic core unavailable
    SymbolicEquation41 = None  # type: ignore


def _evaluate_signals() -> Dict[str, float]:
    if SymbolicEquation41 is None:
        return {
            "coherence_hint": 0.0,
            "risk_hint": 1.0,
            "uncertainty_hint": 1.0,
        }
    ctx = {
        "coherence_hint": 0.8,
        "risk_hint": 0.2,
        "uncertainty_hint": 0.22,
        "mirror": {"consistency": 0.78},
        "metadata": {"asset_path": "web_interface/server"},
    }
    try:
        signals = SymbolicEquation41().evaluate(ctx)
        if hasattr(signals, "to_dict"):
            return dict(signals.to_dict())  # type: ignore[arg-type]
    except Exception:
        pass
    return {
        "coherence_hint": ctx["coherence_hint"],
        "risk_hint": ctx["risk_hint"],
        "uncertainty_hint": ctx["uncertainty_hint"],
    }


def build_asset_manifest() -> Dict[str, object]:
    return {
        "asset_root": "web_interface/static",
        "signals": _evaluate_signals(),
    }


def manifest_path(root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parent
    return base / "asset_manifest.json"


def write_manifest(root: Path | None = None) -> Path:
    path = manifest_path(root)
    payload = build_asset_manifest()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
