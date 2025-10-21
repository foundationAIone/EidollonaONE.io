# serve_web.py
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

ROOT = Path(__file__).parent.resolve()
WEB = ROOT / "web_interface"
ASSETS = WEB / "assets"
FRONTEND = WEB / "frontend"
AWAKENING_ASSETS = ROOT / "awakening_sequence" / "assets"
RPM_MODELS = ROOT / "avatar" / "rpm_ecosystem" / "rendering"

app = FastAPI(title="EidollonaONE Static Server")

# --- CORS (dev) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static mounts ---
# Main mount for your site
app.mount("/webview", StaticFiles(directory=str(WEB), html=True), name="webview")
# Direct mounts so relative paths like "./frontend/components/*.js" work
if FRONTEND.exists():
    app.mount(
        "/frontend", StaticFiles(directory=str(FRONTEND), html=False), name="frontend"
    )
if ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS), html=False), name="assets")
if AWAKENING_ASSETS.exists():
    app.mount(
        "/awakening_assets",
        StaticFiles(directory=str(AWAKENING_ASSETS), html=False),
        name="awakening_assets",
    )
if RPM_MODELS.exists():
    app.mount(
        "/rpm_models",
        StaticFiles(directory=str(RPM_MODELS), html=False),
        name="rpm_models",
    )

# --- Symbolic core imports (optional at runtime) ---
try:
    from symbolic_core.symbolic_equation import symbolic_equation, reality_instance  # type: ignore
except Exception:  # pragma: no cover
    symbolic_equation = None  # type: ignore
    reality_instance = None  # type: ignore


def _viewer_path():
    # prefer the full embodiment viewer if present
    for name in ("avatar_embodiment_viewer.html", "minimal_avatar.html", "index.html"):
        p = WEB / name
        if p.exists():
            return p
    return None


@app.get("/")
def root():
    # Always route root to the stable avatar viewer
    return RedirectResponse(url="/avatar")


@app.get("/avatar")
def avatar():
    # Always point to the clean ESM viewer, forwarding ?model if provided
    es = WEB / "viewer_eidollona_es.html"
    if es.exists():
        # Choose best available local model (or none) and redirect accordingly
        def _redirect_with_model(model_url):
            base = "/webview/viewer_eidollona_es.html"
            return (
                RedirectResponse(url=f"{base}?model={model_url}")
                if model_url
                else RedirectResponse(url=base)
            )

        # Prefer explicit model from query string
        # Note: We cannot directly access Request here without dependency injection;
        # so we inspect via Starlette's global state using app.router, but simpler is to
        # check best local candidates when no explicit model is provided.
        # Auto-pick a local model if present
        candidates = [
            (
                ASSETS / "models" / "eidollona.glb",
                "/webview/assets/models/eidollona.glb",
            ),
            (
                AWAKENING_ASSETS / "eidollona_avatar.glb",
                "/awakening_assets/eidollona_avatar.glb",
            ),
            (
                RPM_MODELS / "eidollonas_body_frame.glb",
                "/rpm_models/eidollonas_body_frame.glb",
            ),
        ]
        chosen = None
        for p, url in candidates:
            try:
                if p.exists():
                    chosen = url
                    break
            except Exception:
                pass
        return _redirect_with_model(chosen)
    # fallback to reset viewer if ESM viewer missing
    reset = WEB / "viewer_avatar_reset.html"
    if reset.exists():
        return RedirectResponse(url="/webview/viewer_avatar_reset.html")
    vp = _viewer_path()
    if vp:
        return FileResponse(str(vp))
    return JSONResponse({"error": "avatar viewer not found"}, status_code=404)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/list")
def list_webview():
    pages = []
    try:
        pages = [p.name for p in WEB.iterdir() if p.suffix.lower() == ".html"]
    except Exception:
        pages = []
    return JSONResponse({"webview": pages})


# --- Symbolic API (lightweight bridge for the viewer) ---
@app.get("/symbolic/metrics")
def symbolic_metrics():
    if not symbolic_equation:
        return JSONResponse({"error": "symbolic core unavailable"}, status_code=503)
    try:
        return JSONResponse(symbolic_equation.get_consciousness_metrics())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/symbolic/diagnostic")
def symbolic_diagnostic():
    if not symbolic_equation:
        return JSONResponse({"error": "symbolic core unavailable"}, status_code=503)
    try:
        return JSONResponse(symbolic_equation.diagnostic())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/symbolic/resonance")
def symbolic_resonance(x: Optional[float] = None):
    if not symbolic_equation:
        return JSONResponse({"error": "symbolic core unavailable"}, status_code=503)
    try:
        val = symbolic_equation.evaluate_resonance(x)
        return JSONResponse({"resonance": float(val)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/symbolic/evaluate")
async def symbolic_evaluate(request: Request):
    if not symbolic_equation:
        return JSONResponse({"error": "symbolic core unavailable"}, status_code=503)
    try:
        payload = await request.json()
        res = symbolic_equation.evaluate(
            payload if isinstance(payload, dict) else {}, {}
        )
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/symbolic/shift")
async def symbolic_shift(request: Request):
    if not symbolic_equation:
        return JSONResponse({"error": "symbolic core unavailable"}, status_code=503)
    try:
        payload = await request.json()
        mag = 0.0
        if isinstance(payload, dict):
            mag = float(payload.get("magnitude", 0.0))
        symbolic_equation.consciousness_shift(mag)
        return JSONResponse(
            {
                "delta_consciousness": float(
                    getattr(symbolic_equation, "delta_consciousness", 0.0)
                )
            }
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/symbolic/state")
def symbolic_state():
    if not symbolic_equation:
        return JSONResponse({"error": "symbolic core unavailable"}, status_code=503)
    try:
        state = {}
        try:
            if reality_instance:
                state["reality"] = reality_instance.get_current_state()
        except Exception:
            state["reality"] = {"reality_state": "unknown"}
        try:
            state["summary"] = symbolic_equation.get_current_state_summary()
            state["metrics"] = symbolic_equation.get_consciousness_metrics()
        except Exception:
            pass
        return JSONResponse(state)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Dummy websocket to silence Simple Browser /ws probes
@app.websocket("/ws")
async def ws_noop(ws: WebSocket):
    await ws.accept()
    try:
        # Keep the connection around; ignore any messages
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
