"""Audit roll-up bot writing nightly summaries."""

from __future__ import annotations

from typing import Any, Dict

from .base_se_bot import SEAwareBot


class AuditRollupBot(SEAwareBot):
    def __init__(self, policy: Dict[str, Any]):
        super().__init__("audit_rollup", policy)

    def nightly(self, tail_info: Dict[str, Any]) -> None:
        context = self.se_context()
        ok, reasons = self.se_gate(context)
        decision = "ALLOW" if ok else "HOLD"
        self.emit(
            "audit_rollup",
            decision=decision,
            reasons=reasons,
            se=context,
            summary=tail_info,
        )
