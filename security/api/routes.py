from __future__ import annotations

import json
import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from security.auth import allow_rate, check_token
from security.policy import get_policy

router = APIRouter()


def _require_token(token: str) -> None:
    ok, _ = check_token(token)
    if not ok:
        raise HTTPException(status_code=401, detail="unauthorized")


_AUDIT_PATH = os.path.join("logs", "security_api.ndjson")


def _audit(event: str, **payload: Any) -> None:
    record = {"ts": time.time(), "event": event, **payload}
    try:
        os.makedirs("logs", exist_ok=True)
        with open(_AUDIT_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


@router.get("/policy")
def get_sec_policy(token: str = Query(...)):
    _require_token(token)
    policy = get_policy().copy()
    _audit("security_policy", caps=policy.get("caps", {}))
    return {"ok": True, "policy": policy}


@router.get("/rate")
def rate_probe(token: str = Query(...)):
    _require_token(token)
    limit = int(get_policy().get("rate_limit", {}).get("per_min_per_token", 120))
    allowed = allow_rate(token, limit)
    _audit("security_rate", allowed=allowed, per_min_per_token=limit)
    return {"ok": allowed, "per_min_per_token": limit}
