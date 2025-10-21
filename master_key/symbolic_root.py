"""symbolic_root

Root accessor utilities for the master symbolic equation instance. Kept in a
separate tiny module so higher-level packages can:

    from master_key.symbolic_root import get_master_symbolic, evaluate_dict

without importing heavier boot / awakening logic.

Design notes
------------
* Zero side-effects on import (no eager evaluation).
* 3.9-compatible typing (no PEP 604 unions in public surface).
* Provides small convenience wrappers that many endpoints/HUDs need.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from symbolic_core.symbolic_equation_master import (
    MasterSymbolicEquation,
    MasterStateSnapshot,
    get_master_symbolic_singleton,
)


# -------- Core accessors -----------------------------------------------------


def get_master_symbolic() -> MasterSymbolicEquation:
    """Return the process-wide MasterSymbolicEquation singleton."""

    return get_master_symbolic_singleton()


def evaluate_master_state(
    context: Optional[Dict[str, Any]] = None
) -> MasterStateSnapshot:
    """Evaluate SE41 with optional context and return a typed snapshot."""

    return get_master_symbolic().evaluate(context)


def evaluate_dict(context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Evaluate and return a JSON-safe dict snapshot (for APIs/HUDs)."""

    return evaluate_master_state(context).to_dict()


def last_snapshot() -> Optional[MasterStateSnapshot]:
    """Return the last cached snapshot if available (else None)."""

    return get_master_symbolic().last_snapshot()


def ping() -> Dict[str, Any]:
    """Cheap liveness/health probe for orchestration/UI.

    Returns:
        dict with ok flag, timestamp, and (if available) last coherence.
    """

    snap = last_snapshot()
    return {
        "ok": True,
        "ts": float(time.time()),
        "coherence": (snap.coherence if snap else None),
    }


__all__ = [
    "get_master_symbolic",
    "evaluate_master_state",
    "evaluate_dict",
    "last_snapshot",
    "ping",
    "MasterSymbolicEquation",
    "MasterStateSnapshot",
]
