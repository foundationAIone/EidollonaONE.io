"""Court explainer bot summarising panel outcomes."""

from __future__ import annotations

from typing import Any, Dict

from .base_se_bot import SEAwareBot


class CourtExplainerBot(SEAwareBot):
    def __init__(self, policy: Dict[str, Any]):
        super().__init__("court_explainer", policy)

    def explain(self, decision_hash: str, detail: Dict[str, Any]) -> None:
        context = self.se_context()
        ok, reasons = self.se_gate(context)
        panel = {"consensus": "ALLOW" if ok else "HOLD", "dissent": [], "reasons": reasons}
        self.emit(
            "court_transcript",
            decision="ALLOW" if ok else "HOLD",
            reasons=reasons,
            se=context,
            decision_hash=decision_hash,
            detail=detail,
            panel=panel,
        )
