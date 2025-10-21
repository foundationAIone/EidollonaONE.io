from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from resonance.engine import twelve_strands
from security.deps import require_token
from utils.audit import audit_ndjson

router = APIRouter()


@router.post("/tones")
def tones(signals: Dict[str, Any], token: str = Depends(require_token)):
    response = twelve_strands(signals)
    audit_ndjson("resonance_tones", token=token, signals=signals, result=response)
    return {"ok": True, "resonance": response}
