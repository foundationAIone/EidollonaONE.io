"""SAFE execution handler used by trading pipeline."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping

from ai_core.common import GateDecisionDict, as_gate_decision


def _ensure_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
        return list(value)
    return []


class ExecutionHandler:
    """Transform strategy plans into execution intents under SAFE gates."""

    def to_intents(
        self,
        plan: Mapping[str, Any],
        gate: Any,
        ctx: Mapping[str, Any],
    ) -> Dict[str, Any]:
        raw_gate: Mapping[str, Any]
        if isinstance(gate, Mapping):
            raw_gate = gate
        else:
            raw_gate = {
                "decision": getattr(gate, "decision", None),
                "reason": getattr(gate, "reason", None),
                "score": getattr(gate, "score", None),
            }
        gate_payload: GateDecisionDict = as_gate_decision(raw_gate)

        intents = _ensure_list(plan.get("intents"))
        sanitized = [self._sanitize_intent(intent) for intent in intents]
        base: Dict[str, Any] = {
            "decision": gate_payload["decision"],
            "reason": gate_payload["reason"],
            "score": gate_payload["score"],
            "intents": sanitized,
            "legal": {
                "reviewed": bool(ctx.get("legal_review", True)),
                "notes": ctx.get("legal_notes", "SAFE default"),
            },
        }
        if gate_payload["decision"] != "ALLOW":
            return {
                **base,
                "ok": False,
                "hint": "Raise FZ1≥0.60, coherence≥0.65, verification≥ethos_min−0.05",
            }
        return {**base, "ok": True}

    def _sanitize_intent(self, intent: Any) -> Dict[str, Any]:
        if isinstance(intent, Mapping):
            return {str(k): v for k, v in intent.items()}
        return {"payload": intent}


__all__ = ["ExecutionHandler"]
