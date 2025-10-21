"""Symbolic vocabulary loader for SAFE dashboard."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


_VOCAB_FILE = Path(__file__).with_name("symbolic_vocabulary.json")


@lru_cache(maxsize=1)
def _load_vocabulary() -> Dict[str, Any]:
    if not _VOCAB_FILE.exists():
        return {
            "intents": ["analyze", "report", "summarize"],
            "domains": ["finance", "governance", "operations"],
            "priorities": ["low", "medium", "high"],
        }
    try:
        with _VOCAB_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {
        "intents": ["analyze", "report", "summarize"],
        "domains": ["finance", "governance", "operations"],
        "priorities": ["low", "medium", "high"],
    }


def refresh() -> Dict[str, Any]:
    """Force a reload of the vocabulary file and return the dictionary."""
    _load_vocabulary.cache_clear()  # type: ignore[attr-defined]
    return _load_vocabulary()


def vocabulary_dict() -> Dict[str, Any]:
    return _load_vocabulary().copy()


__all__ = ["vocabulary_dict", "refresh"]
