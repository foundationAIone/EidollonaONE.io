from __future__ import annotations
from typing import Dict, Any
from symbolic_core.symbolic_equation import SymbolicEquation41
from symbolic_core.context_builder import assemble_se41_context
from utils.audit import audit_ndjson

class AIAgent:
    def __init__(self) -> None:
        self.eq = SymbolicEquation41()
    def sense(self, hint: Dict[str, Any] | None = None) -> Dict[str, Any]:
        ctx = assemble_se41_context(**(hint or {}))
        audit_ndjson("agent_sense", ctx=ctx)
        return ctx
    def think(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        sig = self.eq.evaluate(ctx).to_dict()
        audit_ndjson("agent_think", sig=sig)
        return sig
    def act(self, sig: Dict[str, Any]) -> str:
        gate = "ALLOW" if (sig["coherence"] >= 0.75 and sig["risk"] < 0.6) else "HOLD"
        audit_ndjson("agent_act", gate=gate, sig=sig)
        return gate
