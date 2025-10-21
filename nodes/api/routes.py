from __future__ import annotations

from fastapi import APIRouter, Depends

from nodes.dialogue import open_channel, speak
from security.deps import require_token
from utils.audit import audit_ndjson

router = APIRouter()


@router.post("/open")
def node_open(node_id: str, token: str = Depends(require_token)):
    result = open_channel(node_id, {"consent": True})
    audit_ndjson("node_open", token=token, node_id=node_id, result=result)
    return result


@router.post("/speak")
def node_speak(node_id: str, msg: str, token: str = Depends(require_token)):
    result = speak(node_id, msg)
    audit_ndjson("node_speak", token=token, node_id=node_id, msg=msg, result=result)
    return result
