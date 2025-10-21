from __future__ import annotations

from fastapi import HTTPException, Query

from security.auth import check_token


def require_token(token: str = Query(..., description="Access token")) -> str:
    token_value = (token or "").strip()
    if not token_value:
        raise HTTPException(status_code=401, detail="token required")
    ok, reason = check_token(token_value)
    if not ok:
        raise HTTPException(status_code=401, detail=reason or "unauthorized")
    return token_value
