from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Depends

from security.deps import require_token
from stewardship.ouroboros import diagnose
from utils.audit import audit_ndjson

router = APIRouter()


@router.post("/ouroboros")
def ouro(metrics: Dict[str, float], token: str = Depends(require_token)):
    result = diagnose(metrics)
    audit_ndjson("ouroboros_diagnose", token=token, metrics=metrics, result=result)
    return {"ok": True, "diagnosis": result}
