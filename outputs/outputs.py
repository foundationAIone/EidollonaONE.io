"""Symbolic utilities for the `outputs` data bucket."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import json

from symbolic_core.symbolic_equation import SymbolicEquation41

__all__ = ["OutputsSnapshot", "load_snapshot", "refresh_snapshot"]

_EQ = SymbolicEquation41()
_DEFAULT_CONTEXT = {
    "coherence_hint": 0.82,
    "risk_hint": 0.18,
    "uncertainty_hint": 0.24,
    "mirror": {"consistency": 0.79},
    "metadata": {"bucket": "outputs", "module": "outputs"},
}


@dataclass(slots=True)
class OutputsSnapshot:
    bucket: str
    context: Dict[str, Any]
    signals: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bucket": self.bucket,
            "context": self.context,
            "signals": self.signals,
        }


def _seed_path(root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parent
    return base / "symbolic_seed.json"


def load_snapshot(root: Path | None = None) -> OutputsSnapshot:
    """Load the symbolic seed file, falling back to a live evaluation."""
    path = _seed_path(root)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        ctx = payload.get("context", _DEFAULT_CONTEXT)
        sig = payload.get("signals") or _EQ.evaluate(ctx).to_dict()
        return OutputsSnapshot(bucket="outputs", context=ctx, signals=sig)
    signals = _EQ.evaluate(_DEFAULT_CONTEXT).to_dict()
    snapshot = OutputsSnapshot(bucket="outputs", context=_DEFAULT_CONTEXT, signals=signals)
    path.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
    return snapshot


def refresh_snapshot(context_override: Dict[str, Any] | None = None) -> OutputsSnapshot:
    ctx = dict(_DEFAULT_CONTEXT if context_override is None else _DEFAULT_CONTEXT | context_override)
    ctx.setdefault("metadata", {})
    ctx["metadata"].update({"refreshed_at": datetime.now(timezone.utc).isoformat()})
    signals = _EQ.evaluate(ctx).to_dict()
    snapshot = OutputsSnapshot(bucket="outputs", context=ctx, signals=signals)
    _seed_path().write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
    return snapshot
