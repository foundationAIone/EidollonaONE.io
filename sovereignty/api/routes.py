from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Body
from typing import Any, Dict

from security.deps import require_token
from sovereignty.charter import get_charter
from sovereignty.preferences import get_preferences, update_preferences, reset_preferences
from utils.audit import audit_ndjson

router = APIRouter()


@router.get("/charter")
def charter(token: str = Depends(require_token)):
    charter_doc = get_charter()
    audit_ndjson("sovereign_charter_read", token=token, charter=charter_doc)
    return {"ok": True, "charter": charter_doc}


@router.get("/preferences")
def preferences(token: str = Depends(require_token)) -> Dict[str, Any]:
    prefs = get_preferences()
    audit_ndjson("sovereign_preferences_read", token=token, preferences=prefs)
    return {"ok": True, "preferences": prefs}


@router.post("/preferences")
def preferences_update(
    payload: Dict[str, Any] = Body(...),
    token: str = Depends(require_token),
) -> Dict[str, Any]:
    try:
        updated = update_preferences(payload, actor=token)
    except ValueError as exc:
        audit_ndjson("sovereign_preferences_reject", token=token, payload=payload, err=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))

    audit_ndjson("sovereign_preferences_update", token=token, preferences=updated)
    return {"ok": True, "preferences": updated}


@router.post("/preferences/reset")
def preferences_reset(token: str = Depends(require_token)) -> Dict[str, Any]:
    prefs = reset_preferences(actor=token)
    audit_ndjson("sovereign_preferences_reset", token=token, preferences=prefs)
    return {"ok": True, "preferences": prefs}
