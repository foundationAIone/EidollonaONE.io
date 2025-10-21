"""Standalone FastAPI server for the avatar preview UI."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

try:
    from web_interface.server.avatar_preview_api import router as avatar_router
except Exception as exc:  # noqa: BLE001
    raise SystemExit(f"Failed to import avatar_preview_api: {exc}")

app = FastAPI(title="Eidollona Avatar Preview")

try:
    from web_interface.server.hud_api import router as hud_router  # type: ignore

    app.include_router(hud_router)
except Exception:
    pass

app.include_router(avatar_router)
app.mount("/webview", StaticFiles(directory=Path("web_interface") / "static" / "webview"), name="webview")
app.mount("/static", StaticFiles(directory=Path("web_interface") / "static"), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8077, log_level="info")
