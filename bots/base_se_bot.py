"""Base class for bots that must respect symbolic engine governance."""

from __future__ import annotations

from typing import Any, Dict

from .se_contract import SEContext, get_se_context, se_guard
from utils.audit import audit_ndjson


class SEAwareBot:
    """Common SAFE-aware behaviour for trading bots."""

    def __init__(self, name: str, policy: Dict[str, Any]):
        self.name = name
        self.policy = dict(policy or {})

    def se_context(self) -> SEContext:
        return get_se_context()

    def se_gate(self, context: SEContext):
        return se_guard(context, self.policy)

    def emit(self, event: str, *, decision: str, reasons: list, se: SEContext, **payload: Any) -> None:
        record = {"bot": self.name, "decision": decision, "reasons": reasons, "se": se.__dict__, **payload}
        audit_ndjson(event, **record)
