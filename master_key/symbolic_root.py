"""symbolic_root

Root accessor utilities for the master symbolic equation instance.  Kept in a
separate tiny module so higher-level packages can `from master_key import
get_master_symbolic` without importing the heavier boot / awakening logic.
"""

from __future__ import annotations

from .symbolic_equation_master import (
    get_master_symbolic_singleton,
    MasterSymbolicEquation,
)


def get_master_symbolic() -> MasterSymbolicEquation:
    return get_master_symbolic_singleton()


__all__ = ["get_master_symbolic", "MasterSymbolicEquation"]
