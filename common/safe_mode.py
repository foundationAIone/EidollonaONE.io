"""
SAFE mode helpers and minimal plan approval queue.
Local-only defaults; no sensitive data stored.
"""

from __future__ import annotations
import os
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime

# Default SAFE posture: ON
SAFE_DEFAULT = os.getenv("SAFE_MODE", "1") == "1"

# Minimal in-memory plan approvals (process-local; fine for tests/dev)
_PLANS: Dict[str, Dict[str, Any]] = {}


def is_safe_mode() -> bool:
    return SAFE_DEFAULT


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def require_approval(
    action: str, details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Register a simulated plan and return its id.
    In SAFE mode, actions require explicit approval.
    """
    pid = _hash(f"{action}:{datetime.utcnow().timestamp()}")[:16]
    _PLANS[pid] = {
        "action": action,
        "details": details or {},
        "approved": False,
        "created": datetime.utcnow().isoformat(),
    }
    return {"plan_id": pid, "requires_approval": True}


def approve_plan(plan_id: str, consent_key: str) -> bool:
    if not plan_id or plan_id not in _PLANS:
        return False
    # Store only hashed consent in memory for parity with audit expectations
    _PLANS[plan_id]["consent_hash"] = _hash(consent_key)
    _PLANS[plan_id]["approved"] = True
    _PLANS[plan_id]["approved_at"] = datetime.utcnow().isoformat()
    return True


def is_plan_approved(plan_id: str, consent_key: str) -> bool:
    rec = _PLANS.get(plan_id)
    if not rec:
        return False
    return rec.get("approved") is True and rec.get("consent_hash") == _hash(consent_key)
