from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import time

from .settings import SETTINGS

# Optional integrations
try:  # pragma: no cover - keep router resilient if optional deps are missing
    from common.audit_chain import (
        append_event as audit_append,
        consent_hash as audit_consent_hash,
    )
except Exception:  # pragma: no cover
    audit_append = None
    audit_consent_hash = None

try:  # pragma: no cover
    from autonomous_governance.governance_protocols import get_engine as _get_gov_engine

    _GOV_ENGINE = _get_gov_engine()
except Exception:  # pragma: no cover
    _GOV_ENGINE = None


router = APIRouter(prefix="/governance/fsm", tags=["governance"])

STATE_DIR = Path(__file__).resolve().parent / "state"
FSM_PATH = STATE_DIR / "gov_fsm.json"
MAP_PATH = STATE_DIR / "plan_fsm_map.json"


def _ensure_state():
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        if not FSM_PATH.exists():
            FSM_PATH.write_text("[]", encoding="utf-8")
        if not MAP_PATH.exists():
            MAP_PATH.write_text("{}", encoding="utf-8")
    except Exception:
        pass


def _load() -> List[Dict[str, Any]]:
    try:
        data = json.loads(FSM_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(items: List[Dict[str, Any]]):
    try:
        FSM_PATH.write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _load_map() -> Dict[str, str]:
    try:
        return json.loads(MAP_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_map(m: Dict[str, str]):
    try:
        MAP_PATH.write_text(
            json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _find(items: List[Dict[str, Any]], fid: str) -> Optional[Dict[str, Any]]:
    for it in items:
        if it.get("id") == fid:
            return it
    return None


def _authz(
    action: str, actor: str = "system", context: Optional[Dict[str, Any]] = None
) -> None:
    if _GOV_ENGINE is None:
        # When engine is missing, deny everything (SAFE default)
        raise HTTPException(503, "governance engine unavailable")
    res = _GOV_ENGINE.check_authorization(
        action=action, actor=actor, context=context or {}
    )
    if not res.get("allowed"):
        raise HTTPException(403, f"not authorized: {res.get('reason','deny')}")


def _audit(actor: str, action: str, ctx: Dict[str, Any], payload: Dict[str, Any]):
    try:
        if audit_append:
            audit_append(actor=actor, action=action, ctx=ctx, payload=payload)
    except Exception:
        # Non-fatal; keep API resilient
        pass


def _ctx(request: Optional[Request]) -> Dict[str, Any]:
    return {
        "ip": (
            getattr(request.client, "host", "local")
            if request and request.client
            else "local"
        ),
        "SAFE_MODE": bool(SETTINGS.SAFE_MODE),
        "ts": int(time.time() * 1000),
    }


class CreateBody(BaseModel):
    action: str
    details: Dict[str, Any] = {}
    actor: Optional[str] = None


class IdBody(BaseModel):
    id: str
    actor: Optional[str] = None


class ApproveBody(BaseModel):
    id: str
    consent_key: str
    actor: Optional[str] = None


class CompleteBody(BaseModel):
    id: str
    result: Dict[str, Any] = {}
    actor: Optional[str] = None


@router.get("/list")
async def list_items() -> Dict[str, Any]:
    _ensure_state()
    return {"items": _load()}


@router.get("/get")
async def get_item(id: str) -> Dict[str, Any]:
    _ensure_state()
    items = _load()
    it = _find(items, id)
    if not it:
        raise HTTPException(404, "not found")
    return {"item": it}


@router.post("/create")
async def create(body: CreateBody, request: Request) -> Dict[str, Any]:
    _ensure_state()
    actor = (body.actor or "programmerONE").strip() or "programmerONE"
    _authz("fsm.create", actor=actor, context={"action": body.action})
    items = _load()
    fid = f"fsm_{int(time.time()*1000)}"
    rec = {
        "id": fid,
        "action": body.action,
        "details": body.details or {},
        "state": "proposed",
        "created_ts": time.time(),
        "history": [{"state": "proposed", "ts": time.time(), "actor": actor}],
    }
    items.append(rec)
    _save(items)
    _audit(actor, "fsm.create", _ctx(request), {"id": fid, "action": body.action})
    return {"id": fid, "state": rec["state"]}


@router.post("/queue")
async def queue(body: IdBody, request: Request) -> Dict[str, Any]:
    _ensure_state()
    actor = (body.actor or "programmerONE").strip() or "programmerONE"
    _authz("fsm.queue", actor=actor, context={"id": body.id})
    items = _load()
    it = _find(items, body.id)
    if not it:
        raise HTTPException(404, "not found")
    if it.get("state") not in ("proposed",):
        raise HTTPException(400, "invalid state transition")
    it["state"] = "queued"
    it.setdefault("history", []).append(
        {"state": "queued", "ts": time.time(), "actor": actor}
    )
    _save(items)
    _audit(actor, "fsm.queue", _ctx(request), {"id": body.id})
    return {"id": body.id, "state": it["state"]}


@router.post("/approve")
async def approve(body: ApproveBody, request: Request) -> Dict[str, Any]:
    _ensure_state()
    actor = (body.actor or "programmerONE").strip() or "programmerONE"
    _authz("fsm.approve", actor=actor, context={"id": body.id})
    items = _load()
    it = _find(items, body.id)
    if not it:
        raise HTTPException(404, "not found")
    if it.get("state") not in ("queued",):
        raise HTTPException(400, "invalid state transition")
    # Record hashed consent only
    ch = ""
    try:
        ch = audit_consent_hash(body.consent_key) if audit_consent_hash else ""
    except Exception:
        ch = ""
    it["state"] = "approved"
    it.setdefault("history", []).append(
        {"state": "approved", "ts": time.time(), "actor": actor, "consent_hash": ch}
    )
    _save(items)
    _audit(actor, "fsm.approve", _ctx(request), {"id": body.id, "consent_hash": ch})
    return {"id": body.id, "state": it["state"]}


@router.post("/arm")
async def arm(body: IdBody, request: Request) -> Dict[str, Any]:
    _ensure_state()
    actor = (body.actor or "programmerONE").strip() or "programmerONE"
    _authz("fsm.arm", actor=actor, context={"id": body.id})
    if SETTINGS.SAFE_MODE:
        raise HTTPException(403, "SAFE mode must be off to arm")
    items = _load()
    it = _find(items, body.id)
    if not it:
        raise HTTPException(404, "not found")
    if it.get("state") not in ("approved",):
        raise HTTPException(400, "invalid state transition")
    it["state"] = "armed"
    it.setdefault("history", []).append(
        {"state": "armed", "ts": time.time(), "actor": actor}
    )
    _save(items)
    _audit(actor, "fsm.arm", _ctx(request), {"id": body.id})
    return {"id": body.id, "state": it["state"]}


@router.post("/execute")
async def execute(body: IdBody, request: Request) -> Dict[str, Any]:
    _ensure_state()
    actor = (body.actor or "programmerONE").strip() or "programmerONE"
    _authz("fsm.execute", actor=actor, context={"id": body.id})
    items = _load()
    it = _find(items, body.id)
    if not it:
        raise HTTPException(404, "not found")
    if it.get("state") not in ("approved", "armed"):
        raise HTTPException(400, "invalid state transition")
    it["state"] = "executing"
    it.setdefault("history", []).append(
        {"state": "executing", "ts": time.time(), "actor": actor}
    )
    _save(items)
    _audit(actor, "fsm.execute", _ctx(request), {"id": body.id})
    return {"id": body.id, "state": it["state"]}


@router.post("/complete")
async def complete(body: CompleteBody, request: Request) -> Dict[str, Any]:
    _ensure_state()
    actor = (body.actor or "programmerONE").strip() or "programmerONE"
    _authz("fsm.complete", actor=actor, context={"id": body.id})
    items = _load()
    it = _find(items, body.id)
    if not it:
        raise HTTPException(404, "not found")
    if it.get("state") not in ("executing",):
        raise HTTPException(400, "invalid state transition")
    it["state"] = "completed"
    it.setdefault("history", []).append(
        {
            "state": "completed",
            "ts": time.time(),
            "actor": actor,
            "result": body.result or {},
        }
    )
    _save(items)
    _audit(actor, "fsm.complete", _ctx(request), {"id": body.id})
    return {"id": body.id, "state": it["state"]}


@router.post("/cancel")
async def cancel(body: CreateBody, request: Request) -> Dict[str, Any]:
    # Reuse CreateBody for id-less cancel of a new quick item or for reason-only cancel? Keep simple: cancel requires id in details
    _ensure_state()
    actor = (body.actor or "programmerONE").strip() or "programmerONE"
    fid = str(body.details.get("id") or "").strip()
    reason = str(body.details.get("reason") or "").strip()
    if not fid:
        raise HTTPException(400, "id required in details.id")
    _authz("fsm.cancel", actor=actor, context={"id": fid})
    items = _load()
    it = _find(items, fid)
    if not it:
        raise HTTPException(404, "not found")
    if it.get("state") in ("completed", "cancelled", "failed"):
        raise HTTPException(400, "cannot cancel from current state")
    it["state"] = "cancelled"
    it.setdefault("history", []).append(
        {"state": "cancelled", "ts": time.time(), "actor": actor, "reason": reason}
    )
    _save(items)
    _audit(actor, "fsm.cancel", _ctx(request), {"id": fid, "reason": reason})
    return {"id": fid, "state": it["state"]}


# ---------------- Programmatic helpers for integration ----------------
def map_set(plan_id: str, fsm_id: str) -> None:
    _ensure_state()
    m = _load_map()
    m[str(plan_id)] = str(fsm_id)
    _save_map(m)


def map_get(plan_id: str) -> Optional[str]:
    _ensure_state()
    m = _load_map()
    return m.get(str(plan_id))


def fsm_create(
    action: str,
    details: Optional[Dict[str, Any]] = None,
    actor: Optional[str] = None,
    request: Optional[Request] = None,
) -> str:
    """Create a new FSM record and return its id. Raises HTTPException on auth failure."""
    _ensure_state()
    actor = (actor or "programmerONE").strip() or "programmerONE"
    _authz("fsm.create", actor=actor, context={"action": action})
    items = _load()
    fid = f"fsm_{int(time.time()*1000)}"
    rec = {
        "id": fid,
        "action": action,
        "details": details or {},
        "state": "proposed",
        "created_ts": time.time(),
        "history": [{"state": "proposed", "ts": time.time(), "actor": actor}],
    }
    items.append(rec)
    _save(items)
    _audit(actor, "fsm.create", _ctx(request), {"id": fid, "action": action})
    return fid


def fsm_queue(
    fsm_id: str, actor: Optional[str] = None, request: Optional[Request] = None
) -> None:
    _ensure_state()
    actor = (actor or "programmerONE").strip() or "programmerONE"
    _authz("fsm.queue", actor=actor, context={"id": fsm_id})
    items = _load()
    it = _find(items, fsm_id)
    if not it:
        raise HTTPException(404, "not found")
    if it.get("state") not in ("proposed",):
        raise HTTPException(400, "invalid state transition")
    it["state"] = "queued"
    it.setdefault("history", []).append(
        {"state": "queued", "ts": time.time(), "actor": actor}
    )
    _save(items)
    _audit(actor, "fsm.queue", _ctx(request), {"id": fsm_id})


def fsm_approve(
    fsm_id: str,
    consent_key: str,
    actor: Optional[str] = None,
    request: Optional[Request] = None,
) -> None:
    _ensure_state()
    actor = (actor or "programmerONE").strip() or "programmerONE"
    _authz("fsm.approve", actor=actor, context={"id": fsm_id})
    items = _load()
    it = _find(items, fsm_id)
    if not it:
        raise HTTPException(404, "not found")
    if it.get("state") not in ("queued",):
        raise HTTPException(400, "invalid state transition")
    ch = ""
    try:
        ch = audit_consent_hash(consent_key) if audit_consent_hash else ""
    except Exception:
        ch = ""
    it["state"] = "approved"
    it.setdefault("history", []).append(
        {"state": "approved", "ts": time.time(), "actor": actor, "consent_hash": ch}
    )
    _save(items)
    _audit(actor, "fsm.approve", _ctx(request), {"id": fsm_id, "consent_hash": ch})


def fsm_execute(
    fsm_id: str, actor: Optional[str] = None, request: Optional[Request] = None
) -> None:
    _ensure_state()
    actor = (actor or "programmerONE").strip() or "programmerONE"
    _authz("fsm.execute", actor=actor, context={"id": fsm_id})
    items = _load()
    it = _find(items, fsm_id)
    if not it:
        raise HTTPException(404, "not found")
    if it.get("state") not in ("approved", "armed"):
        raise HTTPException(400, "invalid state transition")
    it["state"] = "executing"
    it.setdefault("history", []).append(
        {"state": "executing", "ts": time.time(), "actor": actor}
    )
    _save(items)
    _audit(actor, "fsm.execute", _ctx(request), {"id": fsm_id})


def fsm_complete(
    fsm_id: str,
    result: Optional[Dict[str, Any]] = None,
    actor: Optional[str] = None,
    request: Optional[Request] = None,
) -> None:
    _ensure_state()
    actor = (actor or "programmerONE").strip() or "programmerONE"
    _authz("fsm.complete", actor=actor, context={"id": fsm_id})
    items = _load()
    it = _find(items, fsm_id)
    if not it:
        raise HTTPException(404, "not found")
    if it.get("state") not in ("executing",):
        raise HTTPException(400, "invalid state transition")
    it["state"] = "completed"
    it.setdefault("history", []).append(
        {
            "state": "completed",
            "ts": time.time(),
            "actor": actor,
            "result": result or {},
        }
    )
    _save(items)
    _audit(actor, "fsm.complete", _ctx(request), {"id": fsm_id})
