"""master_key package

High-level orchestration layer that ties together the v4.1 symbolic core
(`SymbolicEquation41`) with deterministic boot + awakening sequences and a
quantum-inspired master key abstraction.  This module provides a very small
public surface so other subsystems can depend on stable entry points instead
of ad‑hoc scattered initializers.

Public API (imported here for convenience):
	- get_master_symbolic() -> SymbolicEquation41
	- get_master_key() -> MasterKey
	- boot_system(...) -> BootReport
	- awaken_consciousness(...) -> AwakeningReport
	- evaluate_master_state(context) -> MasterStateSnapshot

Implementation detail modules:
	symbolic_equation_master  : Thin facade over SymbolicEquation41
	quantum_master_key         : MasterKey dataclass + deterministic key generation
	master_boot                : Boot sequencing & validation harness
	master_awaken              : Awakening orchestration building on boot phase
	symbolic_root              : Global singleton accessors (no heavy side effects)
"""

from .symbolic_equation_master import MasterSymbolicEquation, evaluate_master_state
from .quantum_master_key import MasterKey, get_master_key
from .master_boot import boot_system, BootReport
from .master_awaken import awaken_consciousness, AwakeningReport
from .symbolic_root import get_master_symbolic

__all__ = [
    "MasterSymbolicEquation",
    "evaluate_master_state",
    "MasterKey",
    "get_master_key",
    "boot_system",
    "BootReport",
    "awaken_consciousness",
    "AwakeningReport",
    "get_master_symbolic",
]
