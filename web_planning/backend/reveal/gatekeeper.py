from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Optional, Any
import os
import time
import hmac
import hashlib

# --- Consent hashing (privacy-preserving) ------------------------------------
_CONSENT_SALT = os.getenv("CONSENT_SALT", "eidollona-consent-salt").encode("utf-8")


def _hash_consent(consent_key: Optional[str]) -> Optional[str]:
    """Return a salted HMAC of the provided consent key; never store plaintext."""
    if not consent_key:
        return None
    return hmac.new(
        _CONSENT_SALT, consent_key.encode("utf-8"), hashlib.sha256
    ).hexdigest()


# --- Data model ----------------------------------------------------------------
@dataclass
class Approval:
    actor: str
    approved: bool
    reason: Optional[str] = None
    at: float = time.time()
    consent_hash: Optional[str] = None
    revoked: bool = False

    def to_public(self) -> Dict[str, Any]:
        # No secrets; only hashed consent is shown
        d = asdict(self)
        # redact internal or noisy fields if you want:
        return d


# --- Gatekeeper ----------------------------------------------------------------
class Gatekeeper:
    """
    Quorum-based approvals with:
      - duplicate actor protection
      - veto support (optional)
      - expiry windows (optional)
      - revocation
      - consent-key hashing (no plaintext)
      - audit hook (best-effort, no hard dependency)
    Backward compatibility:
      submit(actor, approved) still works.
    """

    def __init__(
        self,
        quorum: int = 2,
        allow_veto: bool = False,
        expiry_seconds: Optional[int] = None,
        action_id: Optional[str] = None,
    ):
        if quorum < 1:
            raise ValueError("quorum must be >= 1")
        self.quorum = quorum
        self.allow_veto = allow_veto
        self.expiry_seconds = expiry_seconds
        self.action_id = action_id or f"act_{int(time.time())}"
        self._approvals: Dict[str, Approval] = {}  # actor -> Approval
        self._created_at = time.time()

    # --- Core operations -------------------------------------------------------
    def submit(
        self,
        actor: str,
        approved: bool,
        consent_key: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Approval:
        """Add or replace an actor's approval. Idempotent per actor."""
        self._ensure_not_expired()

        entry = Approval(
            actor=actor,
            approved=approved,
            reason=reason,
            at=time.time(),
            consent_hash=_hash_consent(consent_key),
            revoked=False,
        )
        self._approvals[actor] = entry
        self._audit(
            "approval.submit", {"actor": actor, "approved": approved, "reason": reason}
        )
        return entry

    def revoke(self, actor: str, reason: Optional[str] = None) -> bool:
        """Mark an approval as revoked (does not delete history)."""
        a = self._approvals.get(actor)
        if not a:
            return False
        a.revoked = True
        a.reason = reason or a.reason
        a.at = time.time()
        self._audit("approval.revoke", {"actor": actor, "reason": reason})
        return True

    def reset(self) -> None:
        self._approvals.clear()
        self._created_at = time.time()
        self._audit("approval.reset", {})

    # --- Evaluation ------------------------------------------------------------
    def is_open(self) -> bool:
        """
        Return True if:
          - no veto (if enabled), and
          - non-revoked approvals >= quorum, and
          - not expired (if expiry_seconds set)
        """
        if self._is_expired():
            return False

        if self.allow_veto:
            for a in self._approvals.values():
                if a.approved is False and not a.revoked:
                    return False

        yes = sum(1 for a in self._approvals.values() if a.approved and not a.revoked)
        return yes >= self.quorum

    def status(self) -> Dict[str, Any]:
        """Machine- and UI-friendly snapshot."""
        counts = {"yes": 0, "no": 0, "revoked": 0}
        for a in self._approvals.values():
            if a.revoked:
                counts["revoked"] += 1
            elif a.approved:
                counts["yes"] += 1
            else:
                counts["no"] += 1

        remaining = max(0, self.quorum - counts["yes"])
        return {
            "action_id": self.action_id,
            "quorum": self.quorum,
            "allow_veto": self.allow_veto,
            "expiry_seconds": self.expiry_seconds,
            "created_at": self._created_at,
            "expired": self._is_expired(),
            "open": self.is_open(),
            "remaining_for_quorum": remaining,
            "counts": counts,
            "approvals": [a.to_public() for a in self._approvals.values()],
        }

    # --- Internals -------------------------------------------------------------
    def _is_expired(self) -> bool:
        if not self.expiry_seconds:
            return False
        return (time.time() - self._created_at) > float(self.expiry_seconds)

    def _ensure_not_expired(self) -> None:
        if self._is_expired():
            raise RuntimeError("approval window expired")

    def _audit(self, action: str, payload: Dict[str, Any]) -> None:
        """Best-effort audit hook; no hard dependency."""
        try:
            from common.audit_chain import append_event as _audit_append

            _audit_append(
                actor="gatekeeper",
                action=action,
                ctx={"action_id": self.action_id},
                payload=payload,
            )
        except Exception:
            pass
