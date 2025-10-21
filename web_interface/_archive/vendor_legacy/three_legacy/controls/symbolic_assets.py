"""Symbolic asset manifest for `web_interface/vendor/three_legacy/controls`."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import json

from symbolic_core.symbolic_equation import SymbolicEquation41


def build_asset_manifest() -> Dict[str, float]:
    ctx = {
        "coherence_hint": 0.8,
        "risk_hint": 0.2,
        "uncertainty_hint": 0.22,
        "mirror": {"consistency": 0.78},
        "metadata": {"asset_path": "web_interface/vendor/three_legacy/controls"},
    }
    signals = SymbolicEquation41().evaluate(ctx).to_dict()
    return {
        "asset_root": "web_interface/vendor/three_legacy/controls",
        "signals": signals,
    }


def manifest_path(root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parent
    return base / "asset_manifest.json"


def write_manifest(root: Path | None = None) -> Path:
    path = manifest_path(root)
    payload = build_asset_manifest()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
