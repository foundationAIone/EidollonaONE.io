from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from security.deps import require_token
from utils.audit import audit_ndjson

from ..allowlist import load_allowlist, save_allowlist


router = APIRouter()


class AllowlistPayload(BaseModel):
    domains: Optional[Any]
    read_only: Optional[bool]


@router.get("/allowlist")
def get_allowlist(token: str = Depends(require_token)) -> Dict[str, Any]:
    data = load_allowlist()
    audit_ndjson(
        "allowlist_read",
        token=token,
        read_only=data.get("read_only", True),
        domains=len(data.get("domains", [])),
    )
    return data


@router.post("/allowlist/update")
def update_allowlist(payload: AllowlistPayload, token: str = Depends(require_token)) -> Dict[str, Any]:
    current = load_allowlist()
    if current.get("read_only", True):
        audit_ndjson("allowlist_update_blocked", token=token, read_only=True)
        raise HTTPException(status_code=403, detail="allowlist is read-only")

    base = json.loads(json.dumps(current))
    incoming = payload.dict(exclude_unset=True)
    base.update(incoming)
    try:
        updated = save_allowlist(base)
    except PermissionError:
        audit_ndjson("allowlist_update_blocked", token=token, read_only=True)
        raise HTTPException(status_code=403, detail="allowlist is read-only")

    audit_ndjson(
        "allowlist_update",
        token=token,
        read_only=updated.get("read_only", False),
        domains=len(updated.get("domains", [])),
    )
    return {"ok": True, "allowlist": updated}


@router.post("/allowlist")
def allowlist_mode(payload: Dict[str, Any], token: str = Depends(require_token)) -> Dict[str, Any]:
    mode = str(payload.get("mode", ""))
    audit_ndjson("allowlist_mode", token=token, mode=mode)
    return {"ok": True, "mode": mode or "unspecified"}
