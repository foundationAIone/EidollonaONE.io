"""FastAPI application bootstrap for HUD and auxiliary routers."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI

app = FastAPI(title="EidolonAlpha+ HUD")


# HUD (required)
try:
    from web_interface.server.hud_api import router as hud_router

    app.include_router(hud_router)
except Exception as exc:  # pragma: no cover - fallback path
    exc_detail = str(exc)

    @app.get("/api/hud/signals")
    def _hud_stub() -> Dict[str, Any]:
        return {"error": "hud_api_missing", "detail": exc_detail}


# Optional QPIR snapshot API
try:
    from quantum_probabilistic_information_rendering_system import fastapi_router

    app.include_router(fastapi_router())
except Exception:
    pass


# Optional Citadel endpoints
try:
    from citadel.router import get_router

    _citadel = get_router()

    @app.get("/api/citadel/rooms")
    def list_rooms() -> Any:
        summary = _citadel.summary()
        return summary.get("rooms", {})

    @app.get("/api/citadel/rooms/{room_id}")
    def resolve_room(room_id: str) -> Any:
        room = _citadel.room(room_id)
        if room is None:
            room = _citadel.by_avatar(room_id)
        return room.to_dict() if room else {"error": "not_found"}
except Exception:
    pass
