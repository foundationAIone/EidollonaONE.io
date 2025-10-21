from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Callable

# ----------------------------
# Module metadata
# ----------------------------
__version__ = "1.1.0"  # aligned with audit+FSM-ready guardian
__all__ = [
    "SAFE_MODE",
    "policy_path",
    "get_policy",
    "reload_policy",
    "set_policy_override",
    "clear_policy_override",
    "guard_intake",
    "guard_outbound",
    "metrics",
]

# ----------------------------
# SAFE mode (deny-by-default)
# ----------------------------
SAFE_MODE: bool = str(os.getenv("SAFE_MODE", "1")).strip() not in (
    "0",
    "false",
    "False",
)

# ----------------------------
# Paths & policy cache
# ----------------------------
_pkg_dir = Path(__file__).parent
policy_path = _pkg_dir / "policy.json"

# In-memory policy cache with overrides (thread-safe)
_POLICY_LOCK = threading.RLock()
_POLICY_CACHE: Optional[Dict[str, Any]] = None
_POLICY_OVERRIDE: Optional[Dict[str, Any]] = None
_LAST_LOADED_AT: float = 0.0

# ----------------------------
# Optional audit hook (no-op safe)
# ----------------------------
try:
    from common.audit_chain import append_event as _audit
except Exception:  # pragma: no cover
    _audit = None  # type: ignore


def _audit_event(action: str, payload: Dict[str, Any]) -> None:
    if _audit:
        try:
            _audit(
                actor="guardian",
                action=action,
                ctx={"module": "guardian.init"},
                payload=payload,
            )
        except Exception:
            pass


# ----------------------------
# Policy helpers
# ----------------------------
def _load_policy_from_disk() -> Dict[str, Any]:
    with policy_path.open(encoding="utf-8") as f:
        return json.load(f)


def get_policy() -> Dict[str, Any]:
    """Return the effective policy (disk policy merged with override)."""
    global _POLICY_CACHE, _LAST_LOADED_AT
    with _POLICY_LOCK:
        if _POLICY_CACHE is None:
            base = _load_policy_from_disk()
            eff = dict(base)
            if _POLICY_OVERRIDE:
                eff.update(_POLICY_OVERRIDE)
                eff["_override_active"] = True
            _POLICY_CACHE = eff
            _LAST_LOADED_AT = time.time()
        return _POLICY_CACHE


def reload_policy() -> Dict[str, Any]:
    """Force reload from disk (keeps current override)."""
    global _POLICY_CACHE, _LAST_LOADED_AT
    with _POLICY_LOCK:
        base = _load_policy_from_disk()
        eff = dict(base)
        if _POLICY_OVERRIDE:
            eff.update(_POLICY_OVERRIDE)
            eff["_override_active"] = True
        _POLICY_CACHE = eff
        _LAST_LOADED_AT = time.time()
        _audit_event("policy_reload", {"override_active": bool(_POLICY_OVERRIDE)})
        return _POLICY_CACHE


def set_policy_override(override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a transient, in-memory override (useful for SAFE experiments).
    Never persisted to disk; fully audited.
    """
    global _POLICY_OVERRIDE, _POLICY_CACHE
    with _POLICY_LOCK:
        _POLICY_OVERRIDE = dict(override or {})
        _POLICY_CACHE = None  # force recompute on next access
        eff = get_policy()
        _audit_event("policy_override_set", {"keys": sorted(_POLICY_OVERRIDE.keys())})
        return eff


def clear_policy_override() -> Dict[str, Any]:
    """Remove override and return the reloaded effective policy."""
    global _POLICY_OVERRIDE, _POLICY_CACHE
    with _POLICY_LOCK:
        had = bool(_POLICY_OVERRIDE)
        _POLICY_OVERRIDE = None
        _POLICY_CACHE = None
        eff = get_policy()
        if had:
            _audit_event("policy_override_cleared", {})
        return eff


# ----------------------------
# AI firewall (lazy import to avoid cycles)
# ----------------------------
_guard_intake: Optional[Callable[[str], Tuple[bool, Dict[str, Any]]]] = None
_guard_outbound: Optional[Callable[[str], Tuple[bool, Dict[str, Any]]]] = None


def _ensure_firewall_loaded() -> None:
    global _guard_intake, _guard_outbound
    if _guard_intake and _guard_outbound:
        return
    # Local import to keep init order clean
    from .ai_firewall import guard_intake as gi, guard_outbound as go  # type: ignore

    _guard_intake, _guard_outbound = gi, go


def guard_intake(text: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Ingress guard: sanitize, check Unicode risk, prompt-injection, and link policy.
    Honors current policy (including overrides) through ai_firewall.
    """
    _ensure_firewall_loaded()
    ok, meta = _guard_intake(text)  # type: ignore
    # Fail-closed in SAFE mode: if ai_firewall ever returns undecided, block.
    if ok is None and SAFE_MODE:
        _audit_event("intake_block", {"reason": "undecided_fail_closed"})
        return False, {"reason": "undecided_fail_closed"}
    return bool(ok), meta or {}


def guard_outbound(text: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Egress guard: blocks unsafe URLs and high-entropy/base64 exfiltration.
    Fail-closed in SAFE mode on undecided results.
    """
    _ensure_firewall_loaded()
    ok, meta = _guard_outbound(text)  # type: ignore
    if ok is None and SAFE_MODE:
        _audit_event("outbound_block", {"reason": "undecided_fail_closed"})
        return False, {"reason": "undecided_fail_closed"}
    return bool(ok), meta or {}


# ----------------------------
# Lightweight metrics snapshot
# ----------------------------
_START_TS = time.time()
_BLOCKS = {"intake": 0, "outbound": 0}
_PASSES = {"intake": 0, "outbound": 0}


def _count(ok: bool, kind: str) -> None:
    try:
        if ok:
            _PASSES[kind] += 1
        else:
            _BLOCKS[kind] += 1
    except Exception:
        pass


# Wrap originals to account for metrics without changing public names
_original_guard_intake = guard_intake
_original_guard_outbound = guard_outbound


def guard_intake_wrapped(text: str) -> Tuple[bool, Dict[str, Any]]:
    ok, meta = _original_guard_intake(text)
    _count(ok, "intake")
    return ok, meta


def guard_outbound_wrapped(text: str) -> Tuple[bool, Dict[str, Any]]:
    ok, meta = _original_guard_outbound(text)
    _count(ok, "outbound")
    return ok, meta

# Re-export wrapped names publicly
guard_intake = guard_intake_wrapped
guard_outbound = guard_outbound_wrapped


def metrics() -> Dict[str, Any]:
    """Expose simple Guardian health for dashboards and /metrics endpoints."""
    with _POLICY_LOCK:
        eff = dict(get_policy())
    return {
        "guardian_version": __version__,
        "safe_mode": SAFE_MODE,
        "uptime_sec": round(time.time() - _START_TS, 3),
        "policy_loaded_at": _LAST_LOADED_AT,
        "override_active": eff.get("_override_active", False),
        "passes": dict(_PASSES),
        "blocks": dict(_BLOCKS),
    }
