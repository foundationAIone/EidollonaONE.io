"""Snapshot manifest utilities for `backups/2025-09-18_pre_revert/symbolic_core`."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import json

from symbolic_core.symbolic_equation import SymbolicEquation41


def snapshot_summary() -> Dict[str, float]:
    ctx = {
        "coherence_hint": 0.83,
        "risk_hint": 0.17,
        "uncertainty_hint": 0.26,
        "mirror": {"consistency": 0.8},
        "metadata": {"snapshot": "backups/2025-09-18_pre_revert/symbolic_core"},
    }
    return SymbolicEquation41().evaluate(ctx).to_dict()


def write_summary(path: Path | None = None) -> Path:
    target = path or Path(__file__).resolve().parent / "snapshot_summary.json"
    target.write_text(json.dumps({"signals": snapshot_summary()}, indent=2), encoding="utf-8")
    return target
