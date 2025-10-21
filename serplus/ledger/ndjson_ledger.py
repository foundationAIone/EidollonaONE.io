from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Iterable, List

from serplus.paths import LEDGER_PATH

try:  # pragma: no cover - optional dependency
    from symbolic_core.se41_ext import clamp01 as _se41_clamp01
except Exception:  # pragma: no cover - fallback during testing/dev shells

    def _se41_clamp01(value: float) -> float:
        try:
            numeric = float(value)
        except Exception:
            return 0.0
        if numeric < 0.0:
            return 0.0
        if numeric > 1.0:
            return 1.0
        return numeric


def _ensure() -> None:
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    if not os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, "a", encoding="utf-8"):
            pass


def append(entry: Dict[str, Any]) -> None:
    """Append an entry to the append-only NDJSON ledger."""

    _ensure()
    payload = {"ts": time.time(), **entry}
    with open(LEDGER_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def iter_entries(limit: int = 10_000) -> List[Dict[str, Any]]:
    """Return up to *limit* most recent entries from the ledger."""

    _ensure()
    entries: List[Dict[str, Any]] = []
    with open(LEDGER_PATH, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    if limit <= 0:
        return entries
    return entries[-abs(limit) :]


def _walk(asset: str) -> Iterable[Dict[str, Any]]:
    for entry in iter_entries(10_000_000):
        if entry.get("asset") == asset:
            yield entry


def balances(asset: str = "SER") -> Dict[str, float]:
    """Return computed balances for *asset* by replaying the ledger."""

    bals: Dict[str, float] = {}
    for entry in _walk(asset):
        entry_type = entry.get("type")
        amount = float(entry.get("amount", 0.0))
        if entry_type == "mint":
            target = entry.get("to")
            if target:
                bals[target] = round(bals.get(target, 0.0) + amount, 2)
        elif entry_type == "burn":
            source = entry.get("from")
            if source:
                bals[source] = round(bals.get(source, 0.0) - amount, 2)
        elif entry_type == "transfer":
            source = entry.get("from")
            target = entry.get("to")
            if source:
                bals[source] = round(bals.get(source, 0.0) - amount, 2)
            if target:
                bals[target] = round(bals.get(target, 0.0) + amount, 2)
    return bals


def total_supply(asset: str = "SER") -> float:
    supply = 0.0
    for entry in _walk(asset):
        entry_type = entry.get("type")
        amount = float(entry.get("amount", 0.0))
        if entry_type == "mint":
            supply += amount
        elif entry_type == "burn":
            supply -= amount
    return round(supply, 2)
