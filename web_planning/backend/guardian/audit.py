from __future__ import annotations

import hashlib
import json
import time
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

# Optional centralized, tamper-evident audit chain
try:
    from common.audit_chain import (
        append_event as _chain_append,  # actor, action, ctx, payload
        consent_hash as consent_hash,  # re-exported
        verify_range as verify_range,  # re-exported
    )
except Exception:  # pragma: no cover
    _chain_append = None
    consent_hash = None  # type: ignore
    verify_range = None  # type: ignore


# ----------------------------
# Local JSONL fallback settings
# ----------------------------
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_AUDIT_DIR = os.path.join(_ROOT, "state", "guardian_audit")
_AUDIT_PATH = os.path.join(_AUDIT_DIR, "audit.jsonl")
_MAX_FILE_BYTES = int(os.getenv("GUARDIAN_AUDIT_MAX_BYTES", "5000000"))  # ~5MB
_FALLBACK_ONLY = os.getenv("GUARDIAN_AUDIT_FALLBACK_ONLY", "0") == "1"


def _atomic_append(path: Path, line: str) -> None:
    # For append-only JSONL, plain append is acceptable; still handle rotation
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _rotate_if_needed(path: Path) -> Path:
    try:
        if path.exists() and path.stat().st_size >= _MAX_FILE_BYTES:
            ts = time.strftime("%Y%m%d_%H%M%S")
            rotated = path.with_name(path.stem + f"_{ts}.jsonl")
            path.replace(rotated)
    except Exception:
        pass
    return Path(_AUDIT_PATH)


class AuditLog:
    """
    Governance-ready audit facade for guardian.

    - Delegates to common.audit_chain when available.
    - Maintains a local, tamper-evident JSONL chain as fallback.
    - Preserves backward-compatible API: append(event, actor?), tail(), export().
    - Adds append_event(actor, action, ctx, payload) for structured records.
    """

    def __init__(self) -> None:
        self._chain: List[Dict[str, Any]] = []
        self._last: str = "0" * 64
        try:
            os.makedirs(_AUDIT_DIR, exist_ok=True)
        except Exception:
            pass

    # ---------- Local chain helpers ----------
    def _local_append(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        # Link to last hash for simple tamper-evidence
        rec = dict(rec)
        rec["prev"] = self._last
        blob = json.dumps(rec, sort_keys=True, ensure_ascii=False).encode("utf-8")
        digest = hashlib.sha256(blob).hexdigest()
        rec["hash"] = digest
        self._chain.append(rec)
        self._last = digest
        # persist (best-effort) with rotation
        try:
            p = _rotate_if_needed(Path(_AUDIT_PATH))
            _atomic_append(p, json.dumps(rec, ensure_ascii=False))
        except Exception:
            pass
        return rec

    # ---------- Public API (back-compat) ----------
    def append(self, event: dict, actor: Optional[str] = None) -> Dict[str, Any]:
        """
        Backward-compatible append. Wraps event in a structured record and delegates
        to centralized chain when available, then mirrors to local JSONL.
        """
        actor_name = actor or "system"
        # Attempt centralized audit first (if not forced fallback)
        if _chain_append and not _FALLBACK_ONLY:
            try:
                _chain_append(
                    actor=actor_name,
                    action="guardian.event",
                    ctx={"module": "guardian"},
                    payload=event,
                )
            except Exception:
                pass
        # Always write local record
        rec = {"ts": time.time(), "actor": actor_name, "event": event}
        return self._local_append(rec)

    def append_event(
        self,
        *,
        actor: str,
        action: str,
        ctx: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Structured append. Preferred for new code paths."""
        ctx = ctx or {}
        payload = payload or {}
        # Centralized chain
        if _chain_append and not _FALLBACK_ONLY:
            try:
                _chain_append(actor=actor, action=action, ctx=ctx, payload=payload)
            except Exception:
                pass
        # Local mirror
        rec = {
            "ts": time.time(),
            "actor": actor,
            "action": action,
            "ctx": ctx,
            "payload": payload,
        }
        return self._local_append(rec)

    def export(self) -> List[Dict[str, Any]]:
        return list(self._chain)

    def tail(self, limit: int = 200) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        try:
            p = Path(_AUDIT_PATH)
            if not p.exists():
                return out
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.read().splitlines()
            for ln in lines[-max(1, int(limit)) :] if lines else []:
                try:
                    obj = json.loads(ln)
                    if isinstance(obj, dict):
                        out.append(obj)
                except Exception:
                    continue
        except Exception:
            pass
        return out


# Singleton facade
AUDIT = AuditLog()


# Convenience function mirroring centralized API
def append_event(
    *,
    actor: str,
    action: str,
    ctx: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return AUDIT.append_event(actor=actor, action=action, ctx=ctx, payload=payload)
