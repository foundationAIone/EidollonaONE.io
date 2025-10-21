"""Shared lightweight utilities for optional ai_core dependencies.

These helpers intentionally avoid heavy imports while providing predictable
structures that other modules rely on (for example trading subsystems and
master key tooling). The implementations here are SAFE-friendly stubs that can
be replaced with richer versions when the full stack is available.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Mapping, Optional, TypedDict, cast

logger = logging.getLogger(__name__)

__all__ = [
    "GateDecisionDict",
    "as_gate_decision",
    "load",
    "metrics_to_dict",
]


class GateDecisionDict(TypedDict):
    """Normalized representation for SAFE gate decisions."""

    decision: str
    reason: str
    score: float


_DEFAULT_GATE: GateDecisionDict = {
    "decision": "HOLD",
    "reason": "unspecified",
    "score": 0.0,
}

_ALLOWED_DECISIONS = {"ALLOW", "HOLD", "DENY", "ESCALATE"}


def _is_dataclass_instance(value: Any) -> bool:
    return is_dataclass(value) and not isinstance(value, type)


def as_gate_decision(value: Mapping[str, Any]) -> GateDecisionDict:
    """Convert arbitrary mapping-like payloads into a GateDecisionDict.

    Missing fields fall back to a conservative SAFE default. Scores are coerced to
    floats and decisions are normalized to upper-case SAFE keywords.
    """

    decision_raw = value.get("decision", _DEFAULT_GATE["decision"])
    decision = str(decision_raw or _DEFAULT_GATE["decision"]).upper()
    if decision not in _ALLOWED_DECISIONS:
        decision = _DEFAULT_GATE["decision"]

    reason_raw = value.get("reason", _DEFAULT_GATE["reason"])
    reason = str(reason_raw or _DEFAULT_GATE["reason"])

    score_raw = value.get("score", _DEFAULT_GATE["score"])
    try:
        score = float(score_raw)
    except (TypeError, ValueError):
        score = _DEFAULT_GATE["score"]

    return {
        "decision": decision,
        "reason": reason,
        "score": score,
    }


class _MissingModuleProxy:
    """Very small proxy that returns None for any attribute access."""

    __slots__ = ("module_path",)

    def __init__(self, module_path: str) -> None:
        self.module_path = module_path

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - trivial
        logger.debug("Optional module %%s missing attribute %%s", self.module_path, item)
        return None

    def __call__(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - noop
        logger.debug("Optional module %%s called without implementation", self.module_path)
        return None


def load(module_path: str, attribute: Optional[str] = None) -> Any:
    """Safely import an optional dependency.

    Returns a module object when available, or a lightweight proxy/None when the
    dependency is missing. This keeps callers simple while still allowing rich
    implementations to plug in later.
    """

    try:
        module = importlib.import_module(module_path)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Optional module %%s unavailable: %%s", module_path, exc)
        return None if attribute else _MissingModuleProxy(module_path)

    if attribute is None:
        return module
    return getattr(module, attribute, None)


try:
    from symbolic_core.typing_support import metrics_to_dict as _metrics_to_dict
except Exception:  # pragma: no cover - fallback for minimal environments

    def _metrics_to_dict(value: Any) -> Dict[str, Any]:
        if _is_dataclass_instance(value):
            return asdict(cast(Any, value))
        if isinstance(value, Mapping):
            return dict(value)
        if _is_dataclass_instance(value):
            return asdict(cast(Any, value))
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            try:
                result = to_dict()
            except Exception:
                pass
            else:
                if _is_dataclass_instance(result):
                    return asdict(cast(Any, result))
                if isinstance(result, Mapping):
                    return dict(result)
                return {"value": result}
        return {"value": value}


def metrics_to_dict(value: Any) -> Dict[str, Any]:
    """Convert assorted metric payloads into plain dictionaries."""

    try:
        return _metrics_to_dict(value)
    except Exception:  # pragma: no cover - guard against unusual objects
        if isinstance(value, Mapping):
            return dict(value)
        if _is_dataclass_instance(value):
            return asdict(value)
        return {"value": value}
