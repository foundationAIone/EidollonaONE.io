from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class SocialBotPlan:
    platform: str
    summary: str
    gate: Dict[str, Any]
    legal: Dict[str, str]
    hint: str | None = None

    def as_envelope(self) -> Dict[str, Any]:
        envelope = {
            "bot": self.platform,
            "proposal": self.summary,
            "gate": self.gate,
            "legal": self.legal,
        }
        if self.hint:
            envelope["hint"] = self.hint
        return envelope


class BaseSocialBot:
    platform_name: str

    def plan(self, ctx: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return plan_for(self.platform_name, ctx)


def plan_for(platform: str, ctx: Dict[str, Any] | None = None) -> Dict[str, Any]:
    ctx = ctx or {}
    summary = ctx.get("summary", f"safe narrative update for {platform}")
    gate = {
        "decision": "ALLOW",
        "reason": "baseline_ok",
        "score": 0.82,
    }
    legal = {
        "decision": "BINDING" if platform in {"facebook", "instagram"} else "ADVISORY",
        "jurisdiction": ctx.get("jurisdiction", "global"),
    }
    hint = None if gate["decision"] == "ALLOW" else "requires_manual_review"
    plan = SocialBotPlan(
        platform=platform,
        summary=summary,
        gate=gate,
        legal=legal,
        hint=hint,
    )
    return plan.as_envelope()
