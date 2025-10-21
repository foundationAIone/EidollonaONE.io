"""Consolidated stub: this module now re-exports the canonical SovereigntyEngine.

Previous implementation (ai_core/sovereignty_engine.py) has been unified to reduce
duplication. All code should import from one of:
    from sovereignty.sovereignty_engine import SovereigntyEngine
or (temporarily, for backward compatibility):
    from ai_core.sovereignty_engine import SovereigntyEngine

The canonical implementation lives in `sovereignty/sovereignty_engine.py`.
This stub can be removed after import paths are updated everywhere.
"""

from importlib import import_module

SovereigntyEngine = import_module("sovereignty.sovereignty_engine").SovereigntyEngine  # type: ignore[attr-defined]

__all__ = ["SovereigntyEngine"]
