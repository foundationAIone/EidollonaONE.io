"""Symbolic utilities for the `portfolio_manager_data` data bucket."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from sys import version_info
from pathlib import Path
from typing import Any, Dict

import json

from symbolic_core.symbolic_equation import SymbolicEquation41

__all__ = ["PortfolioManagerDataSnapshot", "load_snapshot", "refresh_snapshot"]

_EQ = SymbolicEquation41()
_DEFAULT_CONTEXT = {
    "coherence_hint": 0.82,
    "risk_hint": 0.18,
    "uncertainty_hint": 0.24,
    "mirror": {"consistency": 0.79},
    "metadata": {"bucket": "portfolio_manager_data", "module": "portfolio_manager_data"},
}

if version_info >= (3, 10):
    _DATACLASS_KWARGS = {"slots": True}
else:
    _DATACLASS_KWARGS = {}


@dataclass(**_DATACLASS_KWARGS)
class PortfolioManagerDataSnapshot:
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


def load_snapshot(root: Path | None = None) -> PortfolioManagerDataSnapshot:
    """Load the symbolic seed file, falling back to a live evaluation."""
    path = _seed_path(root)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        ctx = payload.get("context", _DEFAULT_CONTEXT)
        sig = payload.get("signals") or _EQ.evaluate(ctx).to_dict()
        return PortfolioManagerDataSnapshot(bucket="portfolio_manager_data", context=ctx, signals=sig)
    signals = _EQ.evaluate(_DEFAULT_CONTEXT).to_dict()
    snapshot = PortfolioManagerDataSnapshot(bucket="portfolio_manager_data", context=_DEFAULT_CONTEXT, signals=signals)
    path.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
    return snapshot


def refresh_snapshot(context_override: Dict[str, Any] | None = None) -> PortfolioManagerDataSnapshot:
    ctx = dict(_DEFAULT_CONTEXT if context_override is None else _DEFAULT_CONTEXT | context_override)
    ctx.setdefault("metadata", {})
    ctx["metadata"].update({"refreshed_at": datetime.now(timezone.utc).isoformat()})
    signals = _EQ.evaluate(ctx).to_dict()
    snapshot = PortfolioManagerDataSnapshot(bucket="portfolio_manager_data", context=ctx, signals=signals)
    _seed_path().write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
    return snapshot
