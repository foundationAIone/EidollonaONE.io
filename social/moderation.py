from __future__ import annotations

from dataclasses import dataclass
from typing import List

__all__ = ["ModerationVerdict", "moderate", "redact"]

# Lightweight heuristic lists are SAFE-only; no realtime network calls required.
_BLOCK_TERMS = {
    "shutdown": "shutdown control surfaces",
    "deploy real": "deploy real-world actuators",
    "overload grid": "overload grid directive",
    "live payload": "live payload reference",
    "weapon": "weaponized language",
}

# Words we down-rank but still allow with a caution response.
_SOFT_FLAGS = {"panic", "attack", "exploit"}


@dataclass(frozen=True)
class ModerationVerdict:
    allowed: bool
    reason: str | None
    actions: List[str]

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "reason": self.reason, "actions": list(self.actions)}


def redact(text: str) -> str:
    """Return a redacted version of `text` suitable for SAFE logging."""
    return text[:240] + ("…" if len(text) > 240 else "")


def moderate(text: str | None) -> ModerationVerdict:
    if not text:
        return ModerationVerdict(True, None, ["allow"])

    lowered = text.lower()
    for needle, reason in _BLOCK_TERMS.items():
        if needle in lowered:
            return ModerationVerdict(False, f"blocked: {reason}", ["deny", "shadow_reply"])

    actions = ["allow"]
    if any(flag in lowered for flag in _SOFT_FLAGS):
        actions.append("caution")

    return ModerationVerdict(True, None, actions)
