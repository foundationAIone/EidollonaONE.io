from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from security.deps import require_token
from utils.audit import audit_ndjson

router = APIRouter(prefix="/v1/avatar", tags=["avatars"])


class AvatarIntent(BaseModel):
    session_id: str = Field(..., description="Opaque session identifier")
    text: Optional[str] = Field(None, description="User utterance text")
    intent: Optional[str] = Field(None, description="Named ability to execute")
    args: Dict[str, Any] = Field(default_factory=dict, description="Structured arguments")
    voice_ref: Optional[str] = Field(None, description="Optional voice clip reference")


@dataclass
class ModuleAdapter:
    avatar_id: str
    handle_intent: Callable[[AvatarIntent], Dict[str, Any]]
    fetch_state: Callable[[], Dict[str, Any]]
    fetch_dashboard: Callable[[], Dict[str, Any]]
    stream_events: Optional[Callable[[AvatarIntent], AsyncIterator[Dict[str, Any]]]] = None


_MODULE_CACHE: Dict[str, ModuleAdapter] = {}


def _load_module(avatar_id: str) -> ModuleAdapter:
    if avatar_id in _MODULE_CACHE:
        return _MODULE_CACHE[avatar_id]

    loader: Optional[Callable[[], ModuleAdapter]] = None
    if avatar_id == "fancomp":
        try:
            from avatars.fancomp.abilities import get_module_adapter as loader  # type: ignore
        except Exception:
            loader = None
    elif avatar_id == "serveit":
        try:
            from avatars.serveit.abilities import get_module_adapter as loader  # type: ignore
        except Exception:
            loader = None
    elif avatar_id == "trader":
        try:
            from avatars.trader.abilities import get_module_adapter as loader  # type: ignore
        except Exception:
            loader = None

    if loader is None:
        raise HTTPException(status_code=404, detail=f"avatar '{avatar_id}' not available")

    module = loader()
    if module.avatar_id != avatar_id:
        raise HTTPException(status_code=500, detail="avatar registry mismatch")

    _MODULE_CACHE[avatar_id] = module
    return module


@router.post("/{avatar_id}/intent")
async def route_intent(avatar_id: str, payload: AvatarIntent, token: str = Depends(require_token)) -> JSONResponse:
    module = _load_module(avatar_id)
    audit_ndjson(
        "avatar_intent",
        token=token,
        avatar_id=avatar_id,
        session_id=payload.session_id,
        intent=payload.intent or "text",
    )
    response = module.handle_intent(payload)
    return JSONResponse(response)


@router.get("/{avatar_id}/state")
async def get_state(avatar_id: str, token: str = Depends(require_token)) -> JSONResponse:
    module = _load_module(avatar_id)
    audit_ndjson("avatar_state_read", token=token, avatar_id=avatar_id)
    return JSONResponse(module.fetch_state())


@router.get("/{avatar_id}/dashboard")
async def get_dashboard(avatar_id: str, token: str = Depends(require_token)) -> JSONResponse:
    module = _load_module(avatar_id)
    audit_ndjson("avatar_dash_read", token=token, avatar_id=avatar_id)
    return JSONResponse(module.fetch_dashboard())


async def _stream_with_heartbeat(iterator: AsyncIterator[Dict[str, Any]], interval: float = 20.0):
    try:
        async for item in iterator:
            yield item
    finally:
        # noop to ensure iterator drains cleanly
        return


@router.websocket("/{avatar_id}/stream")
async def stream_events(websocket: WebSocket, avatar_id: str):
    await websocket.accept()
    try:
        init_bytes = await websocket.receive_json()
        payload = AvatarIntent(**init_bytes)
    except Exception:
        await websocket.close(code=1003)
        return

    try:
        module = _load_module(avatar_id)
    except HTTPException:
        await websocket.close(code=4404)
        return

    audit_ndjson(
        "avatar_stream_open",
        token="websocket",
        avatar_id=avatar_id,
        session_id=payload.session_id,
    )

    if module.stream_events is None:
        await websocket.send_json({"event": "unsupported"})
        await websocket.close(code=1000)
        return

    iterator = module.stream_events(payload)

    try:
        async for message in _stream_with_heartbeat(iterator):
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        await websocket.send_json({"event": "error", "detail": str(exc)})
    finally:
        audit_ndjson(
            "avatar_stream_close",
            token="websocket",
            avatar_id=avatar_id,
            session_id=payload.session_id,
        )
        await websocket.close(code=1000)
