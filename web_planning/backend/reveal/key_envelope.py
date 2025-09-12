from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, TYPE_CHECKING
from pathlib import Path
import os
import time
import json
import hmac
import hashlib
import secrets

if TYPE_CHECKING:
    from .gatekeeper import Gatekeeper

# ------------------------------------------------------------------------------
# Config / constants
# ------------------------------------------------------------------------------
_ENVELOPE_DIR = Path(
    os.getenv(
        "REVEAL_STATE_DIR",
        os.path.join(os.path.dirname(__file__), "..", "state", "reveal"),
    )
).resolve()

_ENVELOPE_DIR.mkdir(parents=True, exist_ok=True)

# Salting keeps consent hashes unlinkable across environments
_CONSENT_SALT = os.getenv("CONSENT_SALT", "eidollona-consent-salt").encode("utf-8")


# File where we maintain a small daily JSONL event stream (optional, best-effort)
def _audit_append(actor: str, action: str, payload: Dict[str, Any]) -> None:
    try:
        from common.audit_chain import append_event as _append

        _append(
            actor=actor,
            action=action,
            ctx={"subsystem": "reveal.envelope"},
            payload=payload,
        )
    except Exception:
        pass


def _hmac_key(key: str) -> str:
    """Return salted HMAC-SHA256 of a consent key; plaintext is never persisted."""
    return hmac.new(_CONSENT_SALT, key.encode("utf-8"), hashlib.sha256).hexdigest()


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "env") -> str:
    return f"{prefix}_{int(_now()*1000)}_{secrets.token_hex(6)}"


# ------------------------------------------------------------------------------
# Data model
# ------------------------------------------------------------------------------
@dataclass
class KeyEnvelope:
    """
    A sealed consent envelope:
      - Stores *only* a salted HMAC of the consent key (no plaintext)
      - Optionally references an artifact to unlock (patch, plan id, etc.)
      - Enforces TTL (expiry) and one-time open
    """

    envelope_id: str
    created_at: float
    ttl_seconds: Optional[int] = None
    opened_at: Optional[float] = None
    consent_hash: str = ""  # salted HMAC
    artifact_ref: Optional[str] = None  # e.g., run_id, patch path, plan id
    meta: Dict[str, Any] = None  # free-form metadata

    def to_public(self) -> Dict[str, Any]:
        d = asdict(self)
        # never expose consent hash to callers of public status (keep internal)
        d.pop("consent_hash", None)
        return d

    # -------- persistence ----------
    @property
    def path(self) -> Path:
        return _ENVELOPE_DIR / f"{self.envelope_id}.json"

    def save(self) -> None:
        data = asdict(self)
        try:
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            # best-effort; envelope still lives in memory when created
            pass

    @classmethod
    def load(cls, envelope_id: str) -> "KeyEnvelope":
        p = _ENVELOPE_DIR / f"{envelope_id}.json"
        if not p.exists():
            raise FileNotFoundError(f"envelope '{envelope_id}' not found")
        raw = json.loads(p.read_text(encoding="utf-8"))
        return cls(**raw)

    # -------- state helpers ----------
    def expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return (_now() - self.created_at) > float(self.ttl_seconds)

    def is_opened(self) -> bool:
        return self.opened_at is not None


# ------------------------------------------------------------------------------
# API
# ------------------------------------------------------------------------------
def create_envelope(
    consent_key: str,
    *,
    ttl_seconds: Optional[int] = 3600,
    artifact_ref: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> KeyEnvelope:
    """
    Create and persist a sealed envelope tied to a consent key (stored as a salted HMAC).
    Returns the envelope object (safe to serialize with .to_public()).
    """
    env = KeyEnvelope(
        envelope_id=_new_id("env"),
        created_at=_now(),
        ttl_seconds=ttl_seconds,
        opened_at=None,
        consent_hash=_hmac_key(consent_key),
        artifact_ref=artifact_ref,
        meta=meta or {},
    )
    env.save()
    _audit_append(
        "reveal",
        "envelope.create",
        {
            "envelope_id": env.envelope_id,
            "ttl": ttl_seconds,
            "artifact_ref": artifact_ref,
        },
    )
    return env


def resolve_envelope(
    envelope_id: str,
    *,
    consent_key: str,
    gatekeeper: "Gatekeeper",
    require_open_quorum: bool = True,
) -> Dict[str, Any]:
    """
    Attempt to open an envelope.
    Success requires:
      - envelope exists, not expired, not previously opened
      - consent_key matches stored salted HMAC
      - (optional) gatekeeper.is_open() == True
    On success: marks envelope opened_at and persists; returns public details.
    """
    try:
        env = KeyEnvelope.load(envelope_id)
    except FileNotFoundError:
        _audit_append("reveal", "envelope.resolve.miss", {"envelope_id": envelope_id})
        return {"ok": False, "error": "not_found"}

    # Expiry / already opened
    if env.expired():
        _audit_append(
            "reveal", "envelope.resolve.expired", {"envelope_id": env.envelope_id}
        )
        return {"ok": False, "error": "expired"}
    if env.is_opened():
        _audit_append(
            "reveal", "envelope.resolve.repeat", {"envelope_id": env.envelope_id}
        )
        return {"ok": False, "error": "already_opened"}

    # Consent check (hash-constant comparison)
    provided = _hmac_key(consent_key)
    if not hmac.compare_digest(provided, env.consent_hash):
        _audit_append(
            "reveal", "envelope.resolve.bad_consent", {"envelope_id": env.envelope_id}
        )
        return {"ok": False, "error": "invalid_consent"}

    # Governance gate
    if require_open_quorum and not gatekeeper.is_open():
        _audit_append(
            "reveal",
            "envelope.resolve.quorum_blocked",
            {"envelope_id": env.envelope_id, "gate_status": gatekeeper.status()},
        )
        return {"ok": False, "error": "quorum_not_open"}

    # Open
    env.opened_at = _now()
    env.save()
    _audit_append("reveal", "envelope.resolve.opened", {"envelope_id": env.envelope_id})

    # In many flows, artifact_ref points to something the caller will fetch via a *separate* gated path.
    # We return metadata only; never secrets.
    return {"ok": True, "envelope": env.to_public()}


def status(envelope_id: str) -> Dict[str, Any]:
    """
    Read-only envelope status for UI and audits. Does not expose consent hash.
    """
    try:
        env = KeyEnvelope.load(envelope_id)
    except FileNotFoundError:
        return {"ok": False, "error": "not_found"}

    return {
        "ok": True,
        "envelope": env.to_public(),
        "state": {
            "expired": env.expired(),
            "opened": env.is_opened(),
            "remaining_ttl": (
                None
                if env.ttl_seconds is None
                else max(0, env.ttl_seconds - int(_now() - env.created_at))
            ),
        },
    }


def purge_expired(max_delete: int = 200) -> Dict[str, Any]:
    """
    Best-effort cleanup for expired envelopes. Safe to run periodically.
    """
    deleted = 0
    for path in _ENVELOPE_DIR.glob("env_*.json"):
        if deleted >= max_delete:
            break
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            env = KeyEnvelope(**raw)
            if env.expired() and not env.is_opened():
                path.unlink(missing_ok=True)
                deleted += 1
        except Exception:
            # If unreadable or malformed, skip without crashing
            continue

    if deleted:
        _audit_append("reveal", "envelope.purge", {"deleted": deleted})
    return {"ok": True, "deleted": deleted}
