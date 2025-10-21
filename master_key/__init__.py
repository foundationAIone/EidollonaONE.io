"""master_key package

High-level orchestration layer tying together the v4.1 symbolic core with
boot + awakening sequences and a master key abstraction.

This initializer is tolerant: if advanced classes are unavailable, it exposes
lightweight fallbacks so dependent modules can continue under SAFE posture.
"""

from __future__ import annotations

# Optional import: symbolic facade
try:  # prefer canonical facade if present
	from symbolic_core.symbolic_equation_master import MasterSymbolicEquation  # type: ignore
except Exception:  # fallback minimal facade
	from typing import Any, Dict, Tuple
	from symbolic_core.symbolic_equation import SymbolicEquation41  # type: ignore

	class MasterSymbolicEquation:  # type: ignore
		def __init__(self) -> None:
			self.eq = SymbolicEquation41()
		def evaluate_master_state(self, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
			sig = self.eq.evaluate(context).to_dict()
			c, i = float(sig["coherence"]), float(sig["impetus"])
			if c >= 0.85 and i >= 0.5:
				readiness = "prime_ready"
			elif c >= 0.75:
				readiness = "ready"
			elif c >= 0.60:
				readiness = "warming"
			else:
				readiness = "baseline"
			return readiness, sig

# Optional import: master key
try:
	from .quantum_master_key import MasterKey, get_master_key  # type: ignore
except Exception:  # safe fallback
	import os
	from typing import Dict, TypedDict

	class MasterKey(TypedDict):  # type: ignore
		key: str
		version: str

	def get_master_key() -> Dict[str, str]:  # type: ignore
		return {"key": os.getenv("EID_QUANTUM_MASTER_KEY", "dev-local"), "version": "0.1"}

# Optional import: boot harness
try:
	from .master_boot import BootPolicy, BootReport, boot_system  # type: ignore
except Exception:
	BootPolicy = None  # type: ignore[assignment]
	BootReport = None  # type: ignore[assignment]
	from .master_boot import boot_system  # type: ignore

# Optional import: awaken harness
try:
	from .master_awaken import Stability, AwakeningReport, awaken_consciousness  # type: ignore
except Exception:
	Stability = None  # type: ignore[assignment]
	AwakeningReport = None  # type: ignore[assignment]
	from .master_awaken import awaken_consciousness  # type: ignore

# Optional utilities (soft)
from typing import Any, Dict, Optional, Tuple, cast

_get_master_symbolic_impl = None
_evaluate_master_state_impl = None
_evaluate_dict_impl = None
_last_snapshot_impl = None
_ping_impl = None

try:
	from .symbolic_root import (  # type: ignore
		get_master_symbolic as _get_master_symbolic_impl,  # type: ignore[assignment]
		evaluate_master_state as _evaluate_master_state_impl,  # type: ignore[assignment]
		evaluate_dict as _evaluate_dict_impl,  # type: ignore[assignment]
		last_snapshot as _last_snapshot_impl,  # type: ignore[assignment]
		ping as _ping_impl,  # type: ignore[assignment]
	)
	_HAS_SYMBOLIC_ROOT = True
except Exception:
	_HAS_SYMBOLIC_ROOT = False


def get_master_symbolic() -> MasterSymbolicEquation:
	if _HAS_SYMBOLIC_ROOT and _get_master_symbolic_impl is not None:
		return cast(MasterSymbolicEquation, _get_master_symbolic_impl())
	return MasterSymbolicEquation()


def evaluate_master_state(
	context: Optional[Dict[str, Any]] = None,
) -> Any:
	if _HAS_SYMBOLIC_ROOT and _evaluate_master_state_impl is not None:
		return _evaluate_master_state_impl(context)
	ctx = context or {}
	return MasterSymbolicEquation().evaluate_master_state(ctx)


def evaluate_dict(context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
	if _HAS_SYMBOLIC_ROOT and _evaluate_dict_impl is not None:
		return _evaluate_dict_impl(context)
	ready, payload = evaluate_master_state(context)
	payload = dict(payload)
	payload.setdefault("readiness", ready)
	return payload


def last_snapshot() -> Any:
	if _HAS_SYMBOLIC_ROOT and _last_snapshot_impl is not None:
		return _last_snapshot_impl()
	return None


def ping() -> Dict[str, Any]:
	if _HAS_SYMBOLIC_ROOT and _ping_impl is not None:
		return _ping_impl()
	return {"ok": True}

__all__ = [
	"MasterSymbolicEquation",
	"evaluate_master_state",
	"MasterKey",
	"get_master_key",
	"boot_system",
	"BootPolicy",
	"BootReport",
	"awaken_consciousness",
	"AwakeningReport",
	"Stability",
	"get_master_symbolic",
	"evaluate_dict",
	"last_snapshot",
	"ping",
]
