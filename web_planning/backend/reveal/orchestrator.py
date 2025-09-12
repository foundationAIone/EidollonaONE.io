"""
Reveal orchestrator that composes hardened reveal primitives:
- Deterministic emoji packets with version + checksum
- Gatekeeper (quorum approvals, veto, expiry, revocation)
- Consent-gated key envelopes (TTL + one-time-open)

SAFE-by-default: request_open is preview-only; opening requires quorum.
"""

from typing import Optional, Dict, Any

from .emoji_channel import encode_intent, encode_symbolic, decode_packet
from .gatekeeper import Gatekeeper


class RevealOrchestrator:
    """
    Orchestrates reveal ceremonies with policy-aware, auditable primitives.
    """

    def __init__(
        self,
        *,
        quorum: int = 2,
        allow_veto: bool = False,
        expiry_seconds: Optional[int] = None,
        action_id: Optional[str] = None,
    ) -> None:
        self.gate = Gatekeeper(
            quorum=quorum,
            allow_veto=allow_veto,
            expiry_seconds=expiry_seconds,
            action_id=action_id,
        )

    # ------------------
    # Emoji preview layer
    # ------------------
    def preview(
        self, intent: str, *, meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Produce both legacy and structured emoji previews for an intent.
        Meta may include optional overrides: domain, priority, perf, symbols.
        """
        m = meta or {}
        packet = encode_symbolic(
            intent=intent,
            domain=str(m.get("domain", "ui")),
            priority=str(m.get("priority", "normal")),
            perf=str(m.get("perf", "NORMAL")),
            symbols=int(m.get("symbols", 4)),
        )
        decoded = decode_packet(packet)
        valid_struct = isinstance(packet, list) and len(packet) >= 3
        return {
            "emoji_packet": "".join(packet),
            "emoji_legacy": "".join(encode_intent(intent)),
            "fingerprint": decoded.get("fingerprint"),
            "valid": bool(valid_struct),
            "safe": True,
        }

    def request_open(
        self, intent: str, ciphertext: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Preview-only in SAFE mode. Any ciphertext is ignored at this layer; use
        envelopes + quorum to authorize reveals.
        """
        return self.preview(intent)

    # ------------------
    # Quorum management
    # ------------------
    def submit_approval(
        self,
        actor: str,
        approved: bool,
        *,
        consent_key: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        a = self.gate.submit(
            actor=actor, approved=approved, consent_key=consent_key, reason=reason
        )
        return {"ok": True, "approval": a.to_public(), "status": self.gate.status()}

    def revoke(self, actor: str, *, reason: Optional[str] = None) -> Dict[str, Any]:
        ok = self.gate.revoke(actor, reason=reason)
        return {"ok": ok, "status": self.gate.status()}

    def gate_status(self) -> Dict[str, Any]:
        return self.gate.status()

    def reset_gate(self) -> None:
        self.gate.reset()

    # ------------------
    # Envelope operations
    # ------------------
    def create_envelope(
        self,
        consent_key: str,
        *,
        ttl_seconds: Optional[int] = 3600,
        artifact_ref: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from .key_envelope import create_envelope as _create

        env = _create(
            consent_key, ttl_seconds=ttl_seconds, artifact_ref=artifact_ref, meta=meta
        )
        return {"ok": True, "envelope": env.to_public()}

    def resolve_envelope(
        self, envelope_id: str, *, consent_key: str, require_open_quorum: bool = True
    ) -> Dict[str, Any]:
        from .key_envelope import resolve_envelope as _resolve

        return _resolve(
            envelope_id,
            consent_key=consent_key,
            gatekeeper=self.gate,
            require_open_quorum=require_open_quorum,
        )

    def envelope_status(self, envelope_id: str) -> Dict[str, Any]:
        from .key_envelope import status as _status

        return _status(envelope_id)

    def purge_envelopes(self, *, max_delete: int = 200) -> Dict[str, Any]:
        from .key_envelope import purge_expired as _purge

        return _purge(max_delete=max_delete)
