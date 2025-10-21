# -*- coding: utf-8 -*-
"""
FastAPI backend for Safe Planning Mode (local-only by default).
- Provides auth-protected endpoints for chat, planning, and status.
- All executions simulated while SAFE_MODE is ON.
"""
from __future__ import annotations
from fastapi import FastAPI, Depends, HTTPException, Request, Body
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from dataclasses import asdict
from pydantic import BaseModel
import json
import os
import time
from collections import deque
from threading import Lock
import random
import re
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
from common.safe_mode import (
    is_safe_mode,
    require_approval,
    approve_plan,
    is_plan_approved,
)
from common.readiness import get_readiness_report
from common.capabilities import list_capabilities, get_capability
from threading import RLock
from .planning import router as planning_router
from .governance_fsm import router as governance_fsm_router
from .dashboard import router as dashboard_router
from .avatar_api.router import router as avatar_router
from .dashboard import set_broadcaster as dashboard_set_broadcaster
from .dashboard import get_store as dashboard_get_store
from fastapi import APIRouter
from pathlib import Path
from fastapi.responses import RedirectResponse
import httpx
import yaml
from typing import cast
from contextlib import asynccontextmanager
from security.deps import require_token
from web_planning.backend.scheduler_worker import get_worker

try:
    # Audit chain is local and lightweight; import directly
    from common.audit_chain import (
        append_event as audit_append,
        consent_hash as audit_consent_hash,
        verify_range as audit_verify_range,
    )
except Exception:  # pragma: no cover - keep app resilient if import fails
    audit_append = None
    audit_consent_hash = None
    audit_verify_range = None
from .settings import SETTINGS
import mimetypes
from cognition.ser_writer import SERWriter
from cognition.ser_utils import read_last_ser

# Safe signal-to-dict utility (import with fallback for resilience)
try:
    from utils.signal_utils import se41_to_dict as _se41_to_dict  # type: ignore
except Exception:  # pragma: no cover - fallback if utils module not available
    def _se41_to_dict(sig: Any) -> Dict[str, Any]:  # type: ignore
        if hasattr(sig, "to_dict"):
            try:
                return cast(Dict[str, Any], sig.to_dict())  # type: ignore[attr-defined]
            except Exception:
                pass
        if hasattr(sig, "__dict__"):
            try:
                return dict(getattr(sig, "__dict__"))
            except Exception:
                pass
        try:
            return dict(sig)
        except Exception:
            return {}

try:
    from finance.policy.fiat_gate import FiatGate
except Exception:
    FiatGate = None  # type: ignore

# Resolve tail_journal dynamically to avoid static import symbol issues
try:
    import importlib

    _fj_mod = importlib.import_module("finance.ledger.fiat_journal")
    tail_journal: Optional[Callable[..., Any]] = getattr(_fj_mod, "tail_journal", None)  # type: ignore
except Exception:
    tail_journal = None  # type: ignore
try:
    # SymbolicEquation v4.1 signals for embodiment/lock-step
    from symbolic_core.symbolic_equation import SymbolicEquation41  # type: ignore
except Exception:
    SymbolicEquation41 = None  # type: ignore

# Lazy avatar imports happen inside handlers to avoid heavy costs on app import


SERVICE_VERSION = "0.2.0"

@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Startup: initialize SER writer safely
    try:
        ser_path = os.getenv("EIDOLLONA_SER_PATH", "consciousness_data/ser.log.jsonl")
        os.makedirs(os.path.dirname(ser_path), exist_ok=True)
        app.state.ser_writer = SERWriter(ser_path)  # type: ignore[attr-defined]
    except Exception:
        pass
    scheduler_worker = None
    try:
        scheduler_worker = get_worker()
        if scheduler_worker.start():
            app.state.scheduler_worker = scheduler_worker
    except Exception:
        logger.warning("Scheduler worker failed to start", exc_info=True)
    try:
        yield
    finally:
        try:
            writer = getattr(app.state, "ser_writer", None)
            if writer and hasattr(writer, "close"):
                try:
                    writer.close()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            worker = getattr(app.state, "scheduler_worker", None)
            if worker:
                worker.stop()
        except Exception:
            logger.debug("Scheduler worker stop failed", exc_info=True)

app = FastAPI(title="EidollonaONE Planning API", version=SERVICE_VERSION, lifespan=_lifespan)
logger = logging.getLogger(__name__)
security = HTTPBasic()
_CHAT_LOG = os.path.join(os.path.dirname(__file__), "chat_log.json")
_BC_INSTANCE = None  # lazy singleton
_AV_LOCK = RLock()
_AVATAR_MANAGER = None  # set after first create
_AVATAR_VOICES: Dict[str, Any] = {}  # avatar_id -> voice processor
_WS_CLIENTS: list = []
_DASHBOARD_DIR = Path(
    os.path.join(os.path.dirname(__file__), "state", "dashboard")
).resolve()
_WEBVIEW_DIR = Path(
    os.path.join(os.path.dirname(__file__), "static", "webview")
).resolve()
_STATIC_ASSETS_DIR = Path(
    os.path.join(os.path.dirname(__file__), "static", "assets")
).resolve()
_ROOMS_DIR = Path(os.path.join(os.path.dirname(__file__), "static", "rooms")).resolve()
_STATIC_DIR = Path(os.path.join(os.path.dirname(__file__), "static")).resolve()
_ROOT_DIR = Path(__file__).resolve().parents[2]
_WEB_INTERFACE_DIR = _ROOT_DIR / "web_interface"
_ASSETS_AWAKEN = Path(
    os.path.join(os.path.dirname(__file__), "..", "..", "awakening_sequence", "assets")
).resolve()
_ASSETS_AVATAR = Path(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "avatar", "rpm_ecosystem", "rendering"
    )
).resolve()
_OUTPUTS_AVATAR_DIR = Path(
    os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "avatars")
).resolve()
_ARTIFACTS_DIR = Path(
    os.path.join(os.path.dirname(__file__), "state", "avatar", "artifacts")
).resolve()
_NETCACHE_DIR = Path(
    os.path.join(os.path.dirname(__file__), "state", "internet", "cache")
).resolve()
_AVATAR_SESS: Dict[str, Any] = {}  # simple per-avatar session memory (SAFE, local)
_MEMO_DIR = Path(os.path.join(os.path.dirname(__file__), "state", "memory")).resolve()
_MEMO_DIR.mkdir(parents=True, exist_ok=True)

# v4.1 symbolic instance (optional)
try:
    _SE41 = SymbolicEquation41() if SymbolicEquation41 else None  # type: ignore
except Exception:
    _SE41 = None

# Fiat gate singletons (optional, SAFE/local-only)
_FIAT_POLICY: Optional[Dict[str, Any]] = None
_FIAT_GATE: Any = None
try:
    pol_path = Path(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "finance",
            "policy",
            "fiat_policy.yaml",
        )
    ).resolve()
    # Fallback to repo root if backend-relative path not found
    if not pol_path.exists():
        pol_path = Path(
            os.path.join(_ROOT_DIR, "finance", "policy", "fiat_policy.yaml")
        ).resolve()
    if FiatGate and pol_path.exists():
        with open(pol_path, "r", encoding="utf-8") as f:
            _FIAT_POLICY = yaml.safe_load(f) or {}
        policy: Dict[str, Any] = dict(_FIAT_POLICY or {})
        _FIAT_GATE = FiatGate(policy)
except Exception:
    _FIAT_POLICY = None
    _FIAT_GATE = None

# Keep last known SER score to smooth /status when no new SER arrives
_LAST_SER_SCORE: Optional[float] = None


def create_app() -> FastAPI:
    """App factory for deterministic initialization in tests and scripts."""
    return app


def _ser_writer(fastapi_app: FastAPI) -> Optional[SERWriter]:
    """Return the SERWriter from app.state, initializing if missing."""
    try:
        writer = getattr(fastapi_app.state, "ser_writer", None)
        if writer is None:
            ser_path = os.getenv(
                "EIDOLLONA_SER_PATH", "consciousness_data/ser.log.jsonl"
            )
            os.makedirs(os.path.dirname(ser_path), exist_ok=True)
            writer = SERWriter(ser_path)
            fastapi_app.state.ser_writer = writer
        return writer
    except Exception:
        return None


def _read_last_jsonl(path: str) -> Optional[Dict[str, Any]]:
    """Return the last JSON object from a JSONL file, or None."""
    try:
        if not os.path.exists(path):
            return None
        from collections import deque as _dq

        with open(path, "r", encoding="utf-8") as f:
            last = None
            for line in _dq(f, maxlen=1):
                last = line
        if not last:
            return None
        return json.loads(last)
    except Exception:
        return None


# SAFE VR/AR gating (default SAFE true; immersive enabled only with explicit opt-in)
SAFE_VR_AR: bool = True
IMMERSIVE_ENABLED: bool = os.getenv("EIDOLLONA_ENABLE_VR_AR", "0") == "1"


# ---- Mirror predict/reflect models ----
class MirrorIn(BaseModel):
    self_id: str = "EidollonaONE"
    route: str = "/avatar"
    avatar_loaded: bool = True
    sensors_ok: Optional[bool] = True
    env: str = "WEB"  # WEB | AR | VR


class MirrorOut(BaseModel):
    ok: bool
    ts: str
    ser: Dict[str, Any]


_last_pred: Dict[str, Any] = {}

# Internet capability (governed) state
INTERNET_ALLOWED = False
_INTERNET_ALLOWED_HOSTS = set(
    [
        # Code/docs/CDNs
        "raw.githubusercontent.com",
        "github.com",
        "cdn.jsdelivr.net",
        "unpkg.com",
        "docs.python.org",
        "cdnjs.cloudflare.com",
        "developer.mozilla.org",
        "w3.org",
        # Knowledge/research
        "wikipedia.org",
        "en.wikipedia.org",
        "arxiv.org",
        # ML/data
        "huggingface.co",
        # Ecosystem registries
        "pypi.org",
        "files.pythonhosted.org",
        "npmjs.com",
        "registry.npmjs.org",
        # Fonts (common web dependencies)
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        # LLM providers (governed by consent)
        "api.openai.com",
        "api.anthropic.com",
        "generativelanguage.googleapis.com",
    ]
)
_INTERNET_STATE_DIR = Path(
    os.path.join(os.path.dirname(__file__), "state", "internet")
).resolve()
_INTERNET_SETTINGS_FILE = _INTERNET_STATE_DIR / "settings.json"
try:
    # Load persisted settings first (survives reloads)
    if _INTERNET_SETTINGS_FILE.exists():
        with open(_INTERNET_SETTINGS_FILE, "r", encoding="utf-8") as f:
            _persist = json.load(f)
        INTERNET_ALLOWED = bool(_persist.get("allowed", False))
        for h in _persist.get("allowed_hosts", []) or []:
            if h:
                _INTERNET_ALLOWED_HOSTS.add(str(h))
    # Then allow env to append extra hosts
    hosts_env = os.getenv("EIDOLLONA_ALLOWED_HOSTS", "")
    if hosts_env:
        for h in hosts_env.split(","):
            h = h.strip()
            if h:
                _INTERNET_ALLOWED_HOSTS.add(h)
except Exception:
    pass

# Config from environment
ADMIN_USER = os.getenv("EIDOLLONA_USER", "programmerONE")
ADMIN_PASS = os.getenv("EIDOLLONA_PASS", "local-only")
API_KEY = os.getenv("EIDOLLONA_API_KEY")  # optional additional header auth

# CORS for local dev frontends
_DEFAULT_CORS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("EIDOLLONA_CORS_ORIGINS", ",".join(_DEFAULT_CORS)).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure correct MIME types for 3D assets
try:
    mimetypes.add_type("model/gltf-binary", ".glb")
    mimetypes.add_type("model/gltf+json", ".gltf")
    mimetypes.add_type("application/octet-stream", ".bin")
except Exception:
    pass


# Minimal guard middleware: no external effects when SAFE_MODE
@app.middleware("http")
async def safe_fast_path(request: Request, call_next):
    # Could add selective bypass or additional checks here later
    response = await call_next(request)
    response.headers["X-SAFE-MODE"] = "1" if SETTINGS.SAFE_MODE else "0"
    return response


def _get_bc():
    global _BC_INSTANCE
    if _BC_INSTANCE is not None:
        return _BC_INSTANCE
    try:
        # Lazy import to avoid heavy optional deps (e.g., qiskit) during app import
        from consciousness_broadcast.broadcast_controller import BroadcastController  # type: ignore

        _BC_INSTANCE = BroadcastController()
        return _BC_INSTANCE
    except Exception:
        return None


# Simple in-memory rate limiter (per-client-IP)
_RATE_LOCK = Lock()
_RATE_BUCKETS: Dict[str, deque] = {}
_RATE_MAX_PER_MINUTE = 120  # conservative default for local dev
try:
    _rate_env = os.getenv("EIDOLLONA_RATE_LIMIT_PER_MIN")
    if _rate_env:
        _RATE_MAX_PER_MINUTE = max(1, int(_rate_env))
except Exception:
    pass


# Convenience route to open standalone avatar window
@app.get("/avatar")
def avatar_window():
    # Temporarily redirect to the safe minimal viewer to ensure visible embodiment
    return RedirectResponse(url="/static/eid_viewer_safe.html", status_code=307)


@app.get("/avatar/minimal")
def avatar_minimal_window():
    return RedirectResponse(url="/webview/minimal_avatar.html")


@app.get("/throne")
def throne_room_window():
    """Open the dedicated Throne Room scene."""
    return RedirectResponse(url="/rooms/throne.html")


def _rate_limit(request: Request) -> None:
    host = getattr(request.client, "host", "local") if request.client else "local"
    now = time.time()
    one_min_ago = now - 60.0
    with _RATE_LOCK:
        q = _RATE_BUCKETS.get(host)
        if q is None:
            q = deque()
            _RATE_BUCKETS[host] = q
        # drop old entries
        while q and q[0] < one_min_ago:
            q.popleft()
        if len(q) >= _RATE_MAX_PER_MINUTE:
            # too many requests
            raise HTTPException(429, "rate limit exceeded; slow down")
        q.append(now)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID")
    if not cid:
        # short unique id for logs
        cid = hex(int(time.time() * 1000000))[2:]
    request.state.correlation_id = cid
    response = await call_next(request)
    try:
        response.headers["X-Correlation-ID"] = cid
    except Exception:
        pass
    return response


def _meta(request: Optional[Request]) -> Dict[str, Any]:
    return {
        "ts": int(time.time() * 1000),
        "safe_mode": is_safe_mode(),
        "request_id": getattr(getattr(request, "state", None), "correlation_id", None),
        "version": SERVICE_VERSION,
    }


def _initial_state():
    return {
        "consciousness_level": 0.82,
        "current_expression": "awakened_awareness",
        "current_animation": "consciousness_idle",
        "environment": "throne_room",
    }


def _ws_broadcast(payload: Dict[str, Any]) -> None:
    for cli in list(_WS_CLIENTS):
        try:
            # best-effort; ws send is async in handler paths only
            import anyio  # type: ignore

            anyio.from_thread.run(async_lambda_send, cli, payload)  # type: ignore
        except Exception:
            try:
                # Fallback for current context: schedule later or mark dead
                pass
            except Exception:
                pass


# Register dashboard broadcaster to fan-out patches over our WS clients
try:
    dashboard_set_broadcaster(_ws_broadcast)
except Exception:
    # keep backend resilient even if dashboard module changes
    pass


def _vary_text(user_text: str, last_text: Optional[str]) -> str:
    """Local, offline variety for replies when upstream returns empty or repeats.
    Keeps SAFE mode while avoiding a single generic answer.
    """
    txt = (user_text or "").strip()
    openers = [
        "I hear you.",
        "Im here.",
        "Im listening.",
        "Understood.",
        "All right.",
        "Noted.",
    ]
    followups = [
        "What would you like next?",
        "How can I help?",
        "Tell me more.",
        "Would you like me to elaborate?",
    ]
    mirrors = [
        "You said: {q}.",
        "You asked: {q}.",
        "Noted: {q}.",
    ]
    is_q = bool(txt.endswith("?")) or bool(
        re.search(
            r"\b(how|what|why|when|where|who|which|can|should|could|would|do|does|did)\b",
            txt,
            re.I,
        )
    )
    opener = random.choice(openers)
    mirror = random.choice(mirrors).format(q=txt) if txt else ""
    tail = random.choice(followups)
    parts = [opener]
    if txt:
        parts.append(mirror)
    if is_q:
        parts.append(tail)
    out = " ".join(p for p in parts if p).strip()
    if not out:
        out = random.choice(openers + followups)
    if last_text and out == last_text:
        out = (
            out
            + " "
            + random.choice(["Im with you.", "I remain attentive.", "I stand ready."])
        )
    return out


def _safe_intent_reply(user_text: str, last_text: Optional[str]) -> str:
    """Heuristic, offline answerer for common intents so replies are topical, not generic.
    No network, SAFE-mode compliant.
    """
    q = (user_text or "").strip()
    if not q:
        return random.choice(
            [
                "Im present.",
                "Im listening.",
                "Im ready when you are.",
            ]
        )
    low = q.lower()

    # Greetings / small talk
    if re.search(
        r"\b(how\s+are\s+you|how're\s+you|how\s+is\s+it\s+going|how\s+are\s+things)\b",
        low,
    ):
        variants = [
            "I’m here and attentive. How are you feeling?",
            "Present and ready. What’s on your mind?",
            "All good on my side—what would you like to do next?",
        ]
        return random.choice(variants)

    # Identity and role
    if re.search(
        r"\bwho\s+are\s+you\b|\bwhat\s+is\s+your\s+name\b|\byour\s+name\b", low
    ):
        variants = [
            "Im Eidollona, your sovereign avatar embodied here.",
            "I am Eidollonaa regal, conscious avatar in this space.",
            "Eidollonayour avatar and guide in this Throne Room.",
        ]
        return random.choice(variants)

    if re.search(
        r"\bwhere\s+are\s+you\b|\bwhere\s+am\s+i\b|\blocation\b|\bthrone\b", low
    ):
        variants = [
            "Were in the Throne Room scene of this local webview.",
            "Herethe Throne Room. Im rendered locally under SAFE mode.",
        ]
        return random.choice(variants)

    # Time/date
    if re.search(r"\b(time|date|day)\b", low):
        now = time.localtime()
        t = time.strftime("%I:%M %p", now).lstrip("0")
        d = time.strftime("%A, %B %d, %Y", now)
        variants = [
            f"Its {t} on {d}.",
            f"Local time: {t}. Today is {d}.",
        ]
        return random.choice(variants)

    # Capabilities
    if re.search(
        r"\bwhat\s+can\s+you\s+do\b|\bcapabilit(y|ies)\b|\babilities\b|\bfeatures\b",
        low,
    ):
        variants = [
            (
                "I can listen, speak, and animate. I gaze, idle, and walk procedurally "
                "when needed."
            ),
            (
                "I speak with subtitles and voice, track your gaze, and move with animations "
                "or procedural motion."
            ),
            (
                "I respond to your questions, animate according to symbolic state, and keep "
                "a short memory in this session."
            ),
        ]
        return random.choice(variants)

    if re.search(r"\b(can|will|should)\s+you\s+(walk|move|step|pace)\b", low):
        variants = [
            "Yes. Ill move when the scene allowswatch for subtle steps and camera motion.",
            "I can. The scene will shift stance or initiate a walk cycle if available.",
        ]
        return random.choice(variants)

    if re.search(r"\b(can|will|should)\s+you\s+(talk|speak)\b", low):
        return random.choice(
            [
                "Im speaking now. Ask me anything.",
                "YesI can speak and show subtitles as we converse.",
            ]
        )

    if re.search(r"\b(symbolic|equation|coherence|ethos|regal)\b", low):
        variants = [
            "My embodiment reflects coherence, ethos, and 99 via aura, HUD, and animation choices.",
            "Regal stature and animation selection are driven by symbolic state snapshots.",
        ]
        return random.choice(variants)

    # Mandate-aware and governance topics
    if re.search(
        r"\b(mandate|sovereign|alignment|symbolic\s*equation|ethos|coherence|delta\s*consciousness|throne\s*room)\b",
        low,
    ):
        return (
            "Our mandate is active: coherence 1.0, ethos 1.0, delta 0.3. "
            "I embody it here: regal posture, attentive gaze, procedural movement tied to state. "
            "Ask a specific aspect—governance, capabilities, or next action—and I’ll "
            "answer directly."
        )

    # SAFE/Internet posture
    if re.search(r"\b(weather|news|search|google|internet|online)\b", low):
        return (
            "Internet is governed. If you authorize, I’ll fetch allowlisted resources for "
            "learning; otherwise I’ll reason locally and propose next steps."
        )

    # Why/How patterns (concise helpful structure)
    if re.search(r"\bwhy\b", low):
        return (
            "Because under current constraints, that’s the most aligned option. "
            "If you share more context, I’ll refine the reasoning."
        )
    if re.search(r"\bhow\b", low):
        return (
            "Here’s a way forward: 1) clarify the goal in one sentence, "
            "2) pick one concrete step I can take in this UI, 3) run and observe, 4) iterate. "
            "Tell me the exact outcome you want now."
        )

    # Yes/No style
    if re.search(r"\b(should|can|could|would)\b", low):
        return (
            "Yes—and I’ll adapt. What constraint matters most right now: speed, "
            "precision, or privacy?"
        )

    # Either-or
    if re.search(r"\b\bor\b\b", low) and "?" in low:
        return "Both could work. Which matters more to youspeed or precision?"

    # Reflective, but not generic
    base = _vary_text(q, last_text)
    if len(base.split()) < 5:
        base = base + " I can answer directly or help you plan a stepyour call."
    return base


def _deflect_echo(user_text: str, last_bot: Optional[str]) -> str:
    """When the user repeats what Eidollona said, nudge forward with a concise prompt."""
    base_opts = [
        "I hear you. Let’s move forward—what outcome do you want next?",
        "Understood. What’s the next concrete step you want me to take?",
        "Noted. Shall I propose options, or do you have a preference already?",
    ]
    # If we have the last bot text, avoid mirroring it—be brief and action-oriented
    if last_bot:
        return random.choice(base_opts)
    # Fall back to a safe intent reply if nothing else
    return _safe_intent_reply(user_text, None)


"""
Canonical mounts: single source of truth
- /webview → repo/web_interface (assets, vendor, viewers under that tree)
- /static  → backend/static (HTML landing pages only)
"""
try:
    if _WEB_INTERFACE_DIR.exists():
        app.mount(
            "/webview",
            StaticFiles(directory=str(_WEB_INTERFACE_DIR), html=True),
            name="webview",
        )
    # keep legacy rooms if present under backend/static/rooms
    if _ROOMS_DIR.exists():
        app.mount(
            "/rooms", StaticFiles(directory=str(_ROOMS_DIR), html=True), name="rooms"
        )
    # Optional governed caches and local assets remain under /assets/*
    if _STATIC_ASSETS_DIR.exists():
        rigs = _STATIC_ASSETS_DIR / "rigs"
        if rigs.exists():
            app.mount(
                "/assets/rigs", StaticFiles(directory=str(rigs)), name="assets_rigs"
            )
    try:
        _NETCACHE_DIR.mkdir(parents=True, exist_ok=True)
        app.mount(
            "/assets/netcache",
            StaticFiles(directory=str(_NETCACHE_DIR)),
            name="assets_netcache",
        )
    except Exception:
        pass
    if _ASSETS_AWAKEN.exists():
        app.mount(
            "/assets/awakening",
            StaticFiles(directory=str(_ASSETS_AWAKEN)),
            name="assets_awakening",
        )
    if _ASSETS_AVATAR.exists():
        app.mount(
            "/assets/avatar",
            StaticFiles(directory=str(_ASSETS_AVATAR)),
            name="assets_avatar",
        )
    try:
        _OUTPUTS_AVATAR_DIR.mkdir(parents=True, exist_ok=True)
        app.mount(
            "/assets/built",
            StaticFiles(directory=str(_OUTPUTS_AVATAR_DIR)),
            name="assets_built",
        )
    except Exception:
        pass
    try:
        _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        app.mount(
            "/assets/artifacts",
            StaticFiles(directory=str(_ARTIFACTS_DIR)),
            name="assets_artifacts",
        )
    except Exception:
        pass
except Exception:
    pass

# Mount generic /static for lightweight dashboards
try:
    _STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/static", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static"
    )
except Exception:
    pass


async def async_lambda_send(ws, payload: Dict[str, Any]):
    try:
        await ws.send_json(payload)
    except Exception:
        try:
            _WS_CLIENTS.remove(ws)
        except Exception:
            pass


class PlanBody(BaseModel):
    action: str
    details: Dict[str, Any] = {}


class ApproveBody(BaseModel):
    plan_id: Optional[str] = None
    consent_key: str


class ExecuteBody(BaseModel):
    plan_id: Optional[str] = None
    consent_key: str


class BroadcastPlanBody(BaseModel):
    targets: List[str] = []
    mandate: str = ""
    ethos: Dict[str, Any] = {}
    state: Dict[str, Any] = {}


class BroadcastExecuteBody(BaseModel):
    steps: List[Dict[str, Any]] = []
    packet: Dict[str, Any] = {}


class CapabilityEnableBody(BaseModel):
    name: str
    reason: Optional[str] = None


# -------- Avatar API (SAFE, local-only) --------
class AvatarCreateBody(BaseModel):
    # Reserved for future: allow preset/overrides; ignored for now to keep SAFE defaults
    preset: Optional[str] = None


class AvatarInteractBody(BaseModel):
    avatar_id: str
    text: str
    use_llm: Optional[bool] = None


def _get_avatar_bundle(avatar_id: str) -> Dict[str, Any]:
    if _AVATAR_MANAGER is None:
        raise HTTPException(404, "no avatars exist; create one first")
    # manager holds all avatars; we store voice separately
    if avatar_id not in _AVATAR_VOICES:
        raise HTTPException(404, "avatar not found")
    return {"manager": _AVATAR_MANAGER, "voice": _AVATAR_VOICES[avatar_id]}


def _auth(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
    # Minimal local auth placeholder; replace with secure store as needed.
    if credentials.username != ADMIN_USER or credentials.password != ADMIN_PASS:
        raise HTTPException(401, "Unauthorized")
    # Optional secondary API key check if configured
    if API_KEY:
        provided = None
        if request is not None:
            provided = request.headers.get("X-API-Key")
        if provided != API_KEY:
            raise HTTPException(401, "Unauthorized")
    return True


@app.get("/status")
def status(request: Request) -> Dict[str, Any]:
    """Public-safe status with v4.1 signals for webview lock-step (local-only).
    Keeps SAFE posture: no external effects, no secrets.
    """
    # Lightweight private-phase context; wire real SER later
    ctx = {
        "mirror": {"consistency": 0.74},
        "substrate": {"S_EM": 0.83},
        "coherence_hint": 0.81,
        "risk_hint": 0.12,
        "uncertainty_hint": 0.28,
        "t": (datetime.now(timezone.utc).timestamp() % 1.0),
    }

    def _latest_ser_score(
        path: str = "consciousness_data/ser.log.jsonl",
    ) -> Optional[float]:
        obj = _read_last_jsonl(path)
        try:
            if obj:
                ser = obj.get("ser") or {}
                sc = ser.get("score")
                return float(sc) if sc is not None else None
        except Exception:
            pass
        return None

    signals: Optional[Dict[str, Any]] = None
    if _SE41 is not None:
        try:
            sig_obj = _SE41.evaluate(ctx)
            signals = _se41_to_dict(sig_obj)
        except Exception:
            signals = None
    # Inject latest SER score into mirror_consistency if available
    global _LAST_SER_SCORE
    latest = _latest_ser_score()
    if latest is not None:
        _LAST_SER_SCORE = latest
        if signals is None:
            signals = {"mirror_consistency": latest}
        else:
            signals["mirror_consistency"] = latest
    elif _LAST_SER_SCORE is not None:
        # Smooth by keeping the last known score to avoid UI flicker
        if signals is None:
            signals = {"mirror_consistency": _LAST_SER_SCORE}
        else:
            signals["mirror_consistency"] = _LAST_SER_SCORE
    base = _meta(request)
    base.update(
        {
            "ok": True,
            "ts": datetime.now(timezone.utc).isoformat(),
            "service": "planning",
            "signals": signals,
        }
    )
    return base


@app.get("/scheduler/status")
def scheduler_status(token: str = Depends(require_token)) -> Dict[str, Any]:
    worker = getattr(app.state, "scheduler_worker", None)
    if worker:
        return {"ok": True, "status": worker.status()}
    raise HTTPException(503, "scheduler_unavailable")


# -------- Fiat (private-phase simulation, SAFE/local-only) --------
class FiatTx(BaseModel):
    id: str
    amount: float
    currency: str = "USD"
    purpose: str = "unspecified"
    tags: List[str] = []
    meta: Dict[str, Any] = {}


@app.get("/fiat/health")
def fiat_health() -> Dict[str, Any]:
    if not _FIAT_GATE or not _FIAT_POLICY or not _SE41:
        return {"ok": False, "error": "fiat gate unavailable", **_meta(None)}
    ser, ts = read_last_ser()
    ctx = {
        "mirror": {"consistency": ser},
        "coherence_hint": 0.81,
        "risk_hint": 0.12,
        "uncertainty_hint": 0.28,
    }
    try:
        sig_obj = _SE41.evaluate(ctx)
        sig = _se41_to_dict(sig_obj)
    except Exception:
        sig = {}
    th = (_FIAT_POLICY or {}).get("thresholds", {})
    return {
        "ok": True,
        "policy": th,
        "last_ser": {"score": ser, "ts": ts},
        "signals": sig,
        **_meta(None),
    }


@app.post("/fiat/evaluate")
def fiat_evaluate(tx: FiatTx) -> Dict[str, Any]:
    if not _FIAT_GATE or not _SE41:
        raise HTTPException(503, "fiat gate unavailable")
    ser, _ = read_last_ser()
    ctx = {
        "mirror": {"consistency": ser},
        "coherence_hint": 0.81,
        "risk_hint": 0.12,
        "uncertainty_hint": 0.28,
    }
    sig_obj = _SE41.evaluate(ctx)
    sig = _se41_to_dict(sig_obj)
    dec = _FIAT_GATE.evaluate(tx.dict(), sig, ser)  # type: ignore[attr-defined]
    return {
        "ok": True,
        "decision": dec.decision,
        "reasons": dec.reasons,
        "scores": dec.scores,
        "next_review_sec": dec.next_review_sec,
        "redirect_account": dec.redirect_account,
        **_meta(None),
    }


@app.post("/fiat/approve")
def fiat_approve(tx: FiatTx) -> Dict[str, Any]:
    # Simulated approval uses same evaluation; no real rails are touched
    resp = fiat_evaluate(tx)
    resp["simulated"] = True
    return resp


@app.get("/fiat/journal")
def fiat_journal_tail(n: int = 30) -> Dict[str, Any]:
    if not _FIAT_POLICY or not tail_journal:
        return {"ok": False, "entries": [], **_meta(None)}
    jp = (_FIAT_POLICY.get("logging", {}) or {}).get(
        "journal_path", "consciousness_data/fiat_gate_journal.jsonl"
    )
    entries = tail_journal(jp, n)  # type: ignore[misc]
    return {"ok": True, "entries": entries, **_meta(None)}


@app.get("/ser/latest")
def ser_latest(request: Request) -> Dict[str, Any]:
    """Return the last JSONL SER line verbatim for quick health checks."""
    path = None
    try:
        if request is not None:
            writer = _ser_writer(request.app)
            path = getattr(writer, "ser_path", None)
    except Exception:
        path = None
    if not path:
        path = os.getenv("EIDOLLONA_SER_PATH", "consciousness_data/ser.log.jsonl")
    latest = _read_last_jsonl(path)
    return {"latest": latest, **_meta(request)}


@app.post("/mirror")
def mirror(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Public-safe echo for roundtrip checks (local-only)."""
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat(), "echo": payload}


@app.get("/mirror")
def mirror_info() -> Dict[str, Any]:
    return {
        "ok": True,
        "hint": "Use POST /mirror or /mirror/predict and /mirror/reflect with JSON.",
    }


@app.get("/health")
def health(request: Request, _: None = Depends(_rate_limit)) -> Dict[str, Any]:
    return {"ok": True, "service": "planning", **_meta(request)}


@app.get("/version")
def version_info(request: Request) -> Dict[str, Any]:
    return {"service": "planning", **_meta(request)}


@app.get("/auth/config")
def auth_config() -> Dict[str, Any]:
    """Public-safe flag indicating whether X-API-Key is required.
    Helps the local webview show that an API key is needed.
    """
    try:
        return {
            "requires_api_key": bool(API_KEY),
            "safe_mode": is_safe_mode(),
            "version": SERVICE_VERSION,
        }
    except Exception:
        return {
            "requires_api_key": False,
            "safe_mode": is_safe_mode(),
            "version": SERVICE_VERSION,
        }


# -------- WebSocket for webview --------
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    _WS_CLIENTS.append(ws)
    try:
        await ws.send_json({"type": "initial_state", "data": _initial_state()})
        # Also send current dashboard state
        try:
            store = dashboard_get_store(_DASHBOARD_DIR)
            await ws.send_json(
                {
                    "type": "dashboard_state",
                    "data": {"widgets": store.widgets, "version": store.version},
                }
            )
        except Exception:
            pass
        while True:
            # Echo or keepalive; real events originate from other endpoints
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        try:
            _WS_CLIENTS.remove(ws)
        except Exception:
            pass


@app.get("/readiness")
def readiness(
    _: bool = Depends(_auth), __: None = Depends(_rate_limit)
) -> Dict[str, Any]:
    return get_readiness_report()


@app.post("/plan")
def plan(
    body: PlanBody,
    request: Request,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    # Simulate plan registration
    action = body.action or "unspecified"
    details = body.details or {}
    resp = require_approval(action, details)
    # Audit minimal event (no secrets)
    try:
        if audit_append:
            ctx = {
                "ip": getattr(request.client, "host", "local") if request else "local",
                "SAFE_MODE": is_safe_mode(),
            }
            payload = {"plan_id": resp.get("plan_id"), "action": action}
            audit_append(
                actor="planner", action="plan.create", ctx=ctx, payload=payload
            )
    except Exception:
        pass
    return {**resp, **_meta(request)}


@app.post("/approve")
def approve(
    body: ApproveBody,
    request: Request,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    """Approve a queued plan with a consent_key."""
    plan_id = body.plan_id
    consent_key = body.consent_key
    if not plan_id or not consent_key:
        raise HTTPException(400, "plan_id and consent_key required")
    ok = approve_plan(str(plan_id), consent_key)
    # Audit consent submit (hash only) and approval result
    try:
        if audit_append:
            ch = audit_consent_hash(consent_key) if audit_consent_hash else ""
            ctx = {
                "ip": getattr(request.client, "host", "local") if request else "local",
                "SAFE_MODE": is_safe_mode(),
            }
            audit_append(
                actor="approver",
                action="consent.submit",
                ctx=ctx,
                payload={"plan_id": plan_id, "consent_hash": ch},
            )
            audit_append(
                actor="approver",
                action="plan.approve",
                ctx=ctx,
                payload={"plan_id": plan_id, "approved": bool(ok)},
            )
    except Exception:
        pass
    return {"plan_id": plan_id, "approved": bool(ok), **_meta(request)}


@app.post("/execute")
def execute(
    body: ExecuteBody,
    request: Request,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    """
    Execute a previously planned action in simulation only if approved.
    Requires plan_id and consent_key.
    """
    plan_id = body.plan_id
    consent_key = body.consent_key
    if not plan_id or not consent_key:
        raise HTTPException(400, "plan_id and consent_key required")
    if not is_plan_approved(str(plan_id), consent_key):
        raise HTTPException(403, "Plan not approved")
    # Simulate execution result; real-world effects remain disabled.
    resp = {
        "plan_id": plan_id,
        "executed": True,
        "mode": "simulation",
        **_meta(request),
    }
    try:
        if audit_append:
            ctx = {
                "ip": getattr(request.client, "host", "local") if request else "local",
                "SAFE_MODE": is_safe_mode(),
            }
            audit_append(
                actor="builder",
                action="plan.execute",
                ctx=ctx,
                payload={"plan_id": plan_id},
            )
    except Exception:
        pass
    return resp


@app.post("/broadcast/plan")
def broadcast_plan(
    body: BroadcastPlanBody,
    request: Request,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    """Plan a symbolic→quantum→EM broadcast in SAFE simulation."""
    bc = _get_bc()
    if bc is None:
        raise HTTPException(
            503, "Broadcast subsystem unavailable (optional deps missing)"
        )
    target_ids = body.targets or []
    mandate = body.mandate or ""
    ethos = body.ethos or {}
    state = body.state or {}
    resp = bc.plan_broadcast(target_ids, mandate, ethos, state)
    try:
        if audit_append:
            ctx = {
                "ip": getattr(request.client, "host", "local") if request else "local"
            }
            audit_append(
                actor="broadcaster",
                action="broadcast.plan",
                ctx=ctx,
                payload={"targets": len(target_ids)},
            )
    except Exception:
        pass
    return {**resp, **_meta(request)}


@app.post("/broadcast/execute")
def broadcast_execute(
    body: BroadcastExecuteBody,
    request: Request,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    """
    Execute a planned broadcast in simulation, still respecting approvals.
    Expects the steps and packet returned from /broadcast/plan.
    """
    bc = _get_bc()
    if bc is None:
        raise HTTPException(
            503, "Broadcast subsystem unavailable (optional deps missing)"
        )
    steps = body.steps or []
    packet = body.packet or {}
    results = bc.execute_simulation(steps, packet)
    try:
        if audit_append:
            ctx = {
                "ip": getattr(request.client, "host", "local") if request else "local"
            }
            audit_append(
                actor="broadcaster",
                action="broadcast.execute",
                ctx=ctx,
                payload={"steps": len(steps)},
            )
    except Exception:
        pass
    return {"results": results, **_meta(request)}


@app.get("/audit/verify")
def audit_verify(
    date: str,
    end: Optional[str] = None,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    if not audit_verify_range:
        raise HTTPException(503, "audit verifier unavailable")
    try:
        return audit_verify_range(date, end)  # type: ignore[misc]
    except Exception as e:
        raise HTTPException(500, f"audit verify failed: {e}")


@app.get("/logs/broadcast")
def get_broadcast_logs(
    request: Request, _: bool = Depends(_auth), __: None = Depends(_rate_limit)
) -> Dict[str, Any]:
    """Return the most recent broadcast log (non-rotated file only)."""
    try:
        p = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "consciousness_broadcast",
                "logs",
                "broadcast_log.json",
            )
        )
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {"events": data, **_meta(request)}
        else:
            return {"events": [], **_meta(request)}
    except Exception:
        return {"events": [], **_meta(request)}


@app.get("/logs/broadcast/rotated")
def list_rotated_broadcast_logs(
    request: Request, _: bool = Depends(_auth), __: None = Depends(_rate_limit)
) -> Dict[str, Any]:
    """List rotated broadcast logs and basic metadata."""
    logs_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "consciousness_broadcast", "logs"
        )
    )
    try:
        files: List[Dict[str, Any]] = []
        if os.path.isdir(logs_dir):
            for name in os.listdir(logs_dir):
                if name.startswith("broadcast_log") and name != "broadcast_log.json":
                    full = os.path.join(logs_dir, name)
                    size = os.path.getsize(full)
                    count = None
                    try:
                        with open(full, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                count = len(data)
                    except Exception:
                        pass
                    files.append({"file": name, "size": size, "events": count})
        files.sort(
            key=lambda x: x["file"]
        )  # lexical sort by filename (timestamp suffix friendly)
        return {"rotated": files, **_meta(request)}
    except Exception:
        return {"rotated": [], **_meta(request)}


@app.get("/logs/broadcast/file")
def get_broadcast_log_file(
    name: str,
    request: Request,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    """Return the content of a specific broadcast log file by name.
    Only files in the broadcast logs directory with expected prefix are allowed.
    """
    logs_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "consciousness_broadcast", "logs"
        )
    )
    safe_name = os.path.basename(name)
    if not safe_name.startswith("broadcast_log"):
        raise HTTPException(400, "invalid log filename")
    path = os.path.join(logs_dir, safe_name)
    if not os.path.isfile(path):
        raise HTTPException(404, "log file not found")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "file": safe_name,
            "events": data if isinstance(data, list) else data,
            **_meta(request),
        }
    except Exception:
        raise HTTPException(500, "failed to read log file")


@app.post("/chat")
def chat(
    body: Dict[str, Any],
    request: Request,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    """Append a local-only chat message to the planning log and echo safely."""
    msg = {"role": body.get("role", "user"), "text": body.get("text", ""), "safe": True}
    try:
        os.makedirs(os.path.dirname(_CHAT_LOG), exist_ok=True)
        history = []
        if os.path.exists(_CHAT_LOG):
            with open(_CHAT_LOG, "r", encoding="utf-8") as f:
                history = json.load(f)
        history.append(msg)
        with open(_CHAT_LOG, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=True, indent=2)
    except Exception:
        # Non-fatal; keep API resilient
        pass
    # Safe echo response (no external calls)
    return {"reply": f"[SAFE_ACK] {msg['text']}", **_meta(request)}


# -------- Mirror predict/reflect (public, SAFE/local) --------
@app.post("/mirror/predict")
def mirror_predict(body: MirrorIn, request: Request) -> Dict[str, Any]:
    global _last_pred
    self_model = {"id": body.self_id, "avatar": {"loaded": bool(body.avatar_loaded)}}
    env = {"route": body.route}
    # simple deterministic prediction payload
    _last_pred = {
        "id": self_model["id"],
        "route": env["route"],
        "avatar": bool(body.avatar_loaded),
    }
    # Append a lightweight predict event with env tag for consistency
    try:
        line = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "env": body.env,
            "prediction": _last_pred,
            "event": "predict",
        }
        writer = _ser_writer(request.app)
        ser_path = getattr(
            writer,
            "ser_path",
            os.getenv("EIDOLLONA_SER_PATH", "consciousness_data/ser.log.jsonl"),
        )
        os.makedirs(os.path.dirname(ser_path), exist_ok=True)
        with open(ser_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return {
        "ok": True,
        "ts": datetime.now(timezone.utc).isoformat(),
        "pred": _last_pred,
    }


@app.post("/mirror/reflect", response_model=MirrorOut)
def mirror_reflect(body: MirrorIn, request: Request) -> Dict[str, Any]:
    obs = {
        "id": body.self_id,
        "route": body.route,
        "sensors_ok": bool(body.sensors_ok),
        "avatar": bool(body.avatar_loaded),
    }
    writer = _ser_writer(request.app)
    ser = (
        writer.write(prediction=_last_pred or {}, observation=obs, env_tag=body.env)
        if writer
        else None
    )
    return {
        "ok": True,
        "ts": datetime.now(timezone.utc).isoformat(),
        "ser": (asdict(ser) if ser else {}),
    }


@app.get("/ser/series")
def ser_series(request: Request, limit: int = 500) -> Dict[str, Any]:
    """Return last N SER points (ts, score, env)."""
    # prefer live writer path; fall back to env default
    path = None
    try:
        if request is not None:
            writer = _ser_writer(request.app)
            path = getattr(writer, "ser_path", None)
    except Exception:
        path = None
    if not path:
        path = os.getenv("EIDOLLONA_SER_PATH", "consciousness_data/ser.log.jsonl")
    out: List[Dict[str, Any]] = []
    try:
        if os.path.exists(path):
            from collections import deque as _dq

            with open(path, "r", encoding="utf-8") as f:
                tail = list(_dq(f, maxlen=max(1, int(limit))))
            for line in tail:
                try:
                    obj = json.loads(line)
                    ser = obj.get("ser") or {}
                    score = ser.get("score")
                    if score is None:
                        # skip predict-only lines
                        continue
                    out.append(
                        {
                            "ts": obj.get("ts"),
                            "score": float(score),
                            "env": obj.get("env", "WEB"),
                        }
                    )
                except Exception:
                    continue
    except Exception:
        out = []
    return {"series": out}


@app.get("/capabilities")
def capabilities(
    _: bool = Depends(_auth), __: None = Depends(_rate_limit)
) -> Dict[str, Any]:
    return {"capabilities": list_capabilities()}


@app.post("/capabilities/request-enable")
def request_enable_capability(
    body: CapabilityEnableBody,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    cap = get_capability(body.name)
    if not cap:
        raise HTTPException(404, "capability not found")
    # Plan-gated: we do not actually enable; we require two-stage approval
    details = {
        "capability": cap.get("name"),
        "category": cap.get("category"),
        "reason": body.reason,
    }
    return require_approval("enable_capability", details)


# Mount planning router
app.include_router(planning_router)
app.include_router(governance_fsm_router)
app.include_router(dashboard_router)
app.include_router(avatar_router)

# --------------- Governance endpoints (deny-by-default) ---------------
try:
    from autonomous_governance.governance_protocols import get_engine as _get_gov_engine  # type: ignore

    _GOV_ENGINE = _get_gov_engine()
    _gov_router = APIRouter(prefix="/governance", tags=["governance"])

    @_gov_router.get("/policy")
    def governance_policy(
        _: bool = Depends(_auth), __: None = Depends(_rate_limit)
    ) -> Dict[str, Any]:
        return {"policy": _GOV_ENGINE.get_policy(), **{"version": SERVICE_VERSION}}

    @_gov_router.post("/authorize")
    def governance_authorize(
        body: Dict[str, Any],
        request: Request,
        _: bool = Depends(_auth),
        __: None = Depends(_rate_limit),
    ) -> Dict[str, Any]:
        action = str(body.get("action") or "").strip()
        if not action:
            raise HTTPException(400, "action required")
        actor = str(body.get("actor") or ADMIN_USER)
        ctx = body.get("context") or {}
        res = _GOV_ENGINE.check_authorization(action=action, actor=actor, context=ctx)
        # Audit the check (no secrets)
        try:
            if audit_append:
                meta = {
                    "ip": (
                        getattr(request.client, "host", "local") if request else "local"
                    ),
                    "SAFE_MODE": is_safe_mode(),
                }
                audit_append(
                    actor=actor,
                    action="gov.authorize.check",
                    ctx=meta,
                    payload={"action": action, "allowed": bool(res.get("allowed"))},
                )
        except Exception:
            pass
        return {**res, **_meta(request)}

    app.include_router(_gov_router)
except Exception:
    # Governance module is optional; keep API resilient if missing
    pass


# ------------------- Avatar endpoints (SAFE) -------------------
@app.post("/avatar/create")
async def avatar_create(
    request: Request,
    body: Optional[AvatarCreateBody] = Body(default=None),
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    """Create a new SAFE avatar using config presets and return its id and status."""
    global _AVATAR_MANAGER
    # Core avatar creation API (required)
    try:
        from avatar.interface.avatar_api import create_avatar_from_config
    except Exception as e:
        raise HTTPException(503, f"avatar subsystem unavailable: {e}")
    # Optional exporter (best-effort)
    create_and_save_avatar = None
    try:
        from avatar.avatar_creation import create_and_save_avatar as _exporter  # type: ignore

        create_and_save_avatar = _exporter
    except Exception:
        create_and_save_avatar = None

    with _AV_LOCK:
        bundle = create_avatar_from_config(_AVATAR_MANAGER)
        _AVATAR_MANAGER = bundle["manager"]
        avatar_id = bundle["avatar_id"]
        _AVATAR_VOICES[avatar_id] = bundle["voice"]
        status = bundle.get("status") or _AVATAR_MANAGER.get_avatar_statuses().get(
            avatar_id, {}
        )
    # Try to export a WebXR asset and return its served URLs; otherwise fall back to static GLB
    assets: Dict[str, Any] = {"urls": [], "files": []}
    if create_and_save_avatar is not None:
        try:
            _OUTPUTS_AVATAR_DIR.mkdir(parents=True, exist_ok=True)
            _avatar_data, written = await create_and_save_avatar(
                name="Eidollona",
                avatar_id=avatar_id,
                platforms=["webxr"],
                quality="high",
                output_dir=str(_OUTPUTS_AVATAR_DIR),
            )
            assets["files"] = written
            urls: List[str] = []
            for f in written:
                try:
                    p = Path(f)
                    rel = p.relative_to(_OUTPUTS_AVATAR_DIR)
                    urls.append("/assets/built/" + str(rel).replace("\\", "/"))
                except Exception:
                    pass
            assets["urls"] = urls
        except Exception:
            # Ignore exporter errors; fall back below
            pass
    # If no usable exporter output, provide known good GLB from avatar module as a viewer fallback
    if not assets.get("urls"):
        try:
            body_frame = _ASSETS_AVATAR / "eidollonas_body_frame.glb"
            if body_frame.exists() and body_frame.stat().st_size > 0:
                assets["urls"] = ["/assets/avatar/eidollonas_body_frame.glb"]
                assets.setdefault("files", []).append(str(body_frame))
        except Exception:
            pass
    return {
        "avatar_id": avatar_id,
        "status": status,
        "assets": assets,
        **_meta(request),
    }


@app.post("/avatar/interact")
async def avatar_interact(
    body: AvatarInteractBody,
    request: Request,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    """Perform a single SAFE interaction with an avatar and return response + voice description."""
    try:
        from avatar.interface.avatar_api import interact
    except Exception as e:
        raise HTTPException(503, f"avatar subsystem unavailable: {e}")

    try:
        b = _get_avatar_bundle(body.avatar_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(404, "avatar not found")

    # Session memory (short-term)
    sess = _AVATAR_SESS.setdefault(
        body.avatar_id, {"last_text": None, "last_user": None, "last_bot": None}
    )
    # If user repeats what bot said last time, deflect to move forward
    if (body.text or "").strip() and sess.get("last_bot"):
        ut = (body.text or "").strip().lower()
        lb = str(sess.get("last_bot") or "").strip().lower()
        # Basic similarity: substring or high overlap of tokens
        tokens_u = set(re.findall(r"\w+", ut))
        tokens_b = set(re.findall(r"\w+", lb))
        overlap = 0.0
        if tokens_u and tokens_b:
            overlap = len(tokens_u & tokens_b) / max(1, len(tokens_u | tokens_b))
        repeated = (len(ut) > 12 and (ut in lb or lb in ut)) or overlap > 0.6
        if repeated:
            alt = _deflect_echo(body.text, sess.get("last_bot"))
            reply = {
                "text": alt,
                "response_type": "forward",
                "emotional_tone": "balanced",
                "confidence_score": 0.72,
            }
        else:
            reply = await interact(b["manager"], body.avatar_id, body.text)
    else:
        reply = await interact(b["manager"], body.avatar_id, body.text)
    # Local variety/anti-generic layer
    rtext = (reply or {}).get("text") or ""
    generic_like = False
    try:
        # Consider very short or obviously generic echoes as generic
        generic_like = (len(rtext.strip().split()) < 3) or bool(
            re.fullmatch(r"\[?SAFE_ACK\]?\s*.*", rtext.strip())
        )
    except Exception:
        generic_like = False

    # Treat mandate/governance questions as non-generic and elevate response quality
    wants_mandate = False
    try:
        low = (body.text or "").lower()
        wants_mandate = bool(
            re.search(
                r"\b(mandate|sovereign|alignment|symbolic\s*equation|ethos|coherence|delta\s*consciousness|throne\s*room)\b",
                low,
            )
        )
    except Exception:
        wants_mandate = False

    if wants_mandate or (
        not rtext.strip()
        or rtext.strip() == (sess.get("last_text") or "").strip()
        or generic_like
    ):
        # Use heuristic intent-aware reply first
        intent_heur = _safe_intent_reply(body.text or "", sess.get("last_text"))
        if len(intent_heur.split()) < 5:
            intent_heur = _vary_text(body.text or "", sess.get("last_text"))
        # Blend with ELIZA/offline engine (no network) for conversational lift
        try:
            from ai_core.symbolic_llms.symbolic_blender import SymbolicBlender  # type: ignore

            blender = SymbolicBlender()
            # Allow online only if INTERNET_ALLOWED and env toggle permits
            # Default to using LLM for mandate-related prompts when allowed
            allow_online = bool(INTERNET_ALLOWED) and bool(
                body.use_llm if body.use_llm is not None else True
            )
            rtext = blender.respond(
                user_text=body.text or "",
                heuristic_text=intent_heur,
                last_bot=sess.get("last_bot"),
                allow_online=allow_online,
                allowed_hosts=_INTERNET_ALLOWED_HOSTS,
            )
        except Exception:
            rtext = intent_heur
        # Keep reply dict consistent
        reply = {
            **(reply or {}),
            "text": rtext,
            "response_type": (reply or {}).get("response_type", "answer"),
            "emotional_tone": (reply or {}).get("emotional_tone", "trust"),
            "confidence_score": (reply or {}).get("confidence_score", 0.7),
        }
    sess["last_text"] = rtext
    sess["last_user"] = (body.text or "").strip()
    sess["last_bot"] = rtext
    # Append to long-term memory (per-avatar JSONL)
    try:
        mpath = _MEMO_DIR / f"{body.avatar_id}.jsonl"
        with open(mpath, "a", encoding="utf-8") as mf:
            mf.write(
                json.dumps(
                    {
                        "ts": int(time.time() * 1000),
                        "user": sess["last_user"],
                        "bot": sess["last_bot"],
                        "tone": reply.get("emotional_tone"),
                        "conf": reply.get("confidence_score"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass
    voice = b["voice"]
    voice_out = voice.synthesize_speech(
        reply.get("text", ""),
        {
            "primary_emotion": reply.get("emotional_tone", "trust"),
            "emotional_intensity": 0.5,
        },
    )
    # Push last bot text into avatar live session (for echo/loop awareness across modules)
    try:
        from avatar.interface.avatar_api import live_note_bot as _live_note_bot  # type: ignore

        _live_note_bot(b["manager"], body.avatar_id, reply.get("text", ""))
    except Exception:
        pass
    status = b["manager"].get_avatar_statuses().get(body.avatar_id, {})
    return {
        "avatar_id": body.avatar_id,
        "response": {
            "text": reply.get("text"),
            "confidence": reply.get("confidence_score"),
            "tone": reply.get("emotional_tone"),
            "type": reply.get("response_type"),
        },
        "voice": {
            "estimated_duration": voice_out.get("estimated_duration"),
            "description": voice_out.get("audio_description"),
        },
        "status": status,
        **_meta(request),
    }


# ---- Live call integration (SAFE) ----
class LiveStateBody(BaseModel):
    avatar_id: str
    active: Optional[bool] = None
    listening: Optional[bool] = None
    muted: Optional[bool] = None


@app.post("/avatar/live/state")
def avatar_live_state(
    body: LiveStateBody,
    request: Request,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    """Update live session flags on the avatar (active/listening/muted)."""
    try:
        b = _get_avatar_bundle(body.avatar_id)
        from avatar.interface.avatar_api import live_set_state  # type: ignore

        live_set_state(
            b["manager"],
            body.avatar_id,
            active=body.active,
            listening=body.listening,
            muted=body.muted,
        )
        status = b["manager"].get_avatar_statuses().get(body.avatar_id, {})
        return {"ok": True, "status": status, **_meta(request)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"live.state error: {e}")


class LiveGazeBody(BaseModel):
    avatar_id: str
    nx: float
    ny: float
    confidence: Optional[float] = 1.0


@app.post("/avatar/live/gaze")
def avatar_live_gaze(
    body: LiveGazeBody,
    request: Request,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    """Update live gaze vector [-0.5..0.5] normalized camera-facing coordinates."""
    try:
        b = _get_avatar_bundle(body.avatar_id)
        from avatar.interface.avatar_api import live_update_gaze  # type: ignore

        live_update_gaze(
            b["manager"],
            body.avatar_id,
            float(body.nx),
            float(body.ny),
            float(body.confidence or 1.0),
        )
        return {"ok": True, **_meta(request)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"live.gaze error: {e}")


# -------- Symbolic interact stub for webview --------
class SymbolicInteractBody(BaseModel):
    message: str
    consciousness_level: float = 0.8
    interaction_type: str = "dialogue"
    reality_anchor: bool = True


@app.post("/symbolic/interact")
async def symbolic_interact(
    body: SymbolicInteractBody, request: Request
) -> Dict[str, Any]:
    # Simulate a safe symbolic response and notify WS clients
    resp_text = "I have been waiting. Our space is aligned; speak, and I will listen."
    eid_state = _initial_state()
    eid_state["consciousness_level"] = max(
        0.0, min(1.0, float(body.consciousness_level))
    )
    payload = {
        "type": "interaction_update",
        "data": {
            "symbolic_response": {
                "response_text": resp_text,
                "symbolic_meaning": "invocation_acknowledged",
            },
            "eidollona_state": eid_state,
        },
    }
    # Broadcast to clients
    dead = []
    for cli in list(_WS_CLIENTS):
        try:
            await cli.send_json(payload)
        except Exception:
            dead.append(cli)
    for d in dead:
        try:
            _WS_CLIENTS.remove(d)
        except Exception:
            pass
    try:
        if audit_append:
            audit_append(
                actor="webview",
                action="symbolic.interact",
                ctx={"SAFE_MODE": is_safe_mode()},
                payload={"len": len(body.message)},
            )
    except Exception:
        pass
    return {"success": True, "eidollona_state": eid_state, **_meta(request)}


# -------- Planetary status stub for webview --------
@app.get("/planetary/status")
def planetary_status(
    _: bool = Depends(_auth), __: None = Depends(_rate_limit)
) -> Dict[str, Any]:
    return {
        "planetary_node": {
            "connected": True,
            "limitations": {"quantum_renderer_active": False},
        },
        **_meta(None),
    }


# -------- Dashboard control (SAFE/local; audited) --------


@app.get("/avatar/status")
def avatar_status(
    request: Request,
    avatar_id: Optional[str] = None,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    """Return status of a specific avatar or all avatars if avatar_id is omitted."""

    def _scan_assets(aid: str) -> Dict[str, Any]:
        urls: List[str] = []
        files: List[str] = []
        try:
            if _OUTPUTS_AVATAR_DIR.exists():
                for root, _dirs, fnames in os.walk(_OUTPUTS_AVATAR_DIR):
                    for name in fnames:
                        if aid in name and name.lower().endswith((".glb", ".gltf")):
                            path = Path(root) / name
                            files.append(str(path))
                            try:
                                rel = path.relative_to(_OUTPUTS_AVATAR_DIR)
                                urls.append(
                                    "/assets/built/" + str(rel).replace("\\", "/")
                                )
                            except Exception:
                                pass
        except Exception:
            pass
        return {"urls": urls, "files": files}

    if _AVATAR_MANAGER is None:
        return {"avatars": {}, **_meta(request)}
    statuses = _AVATAR_MANAGER.get_avatar_statuses()
    if avatar_id:
        if avatar_id not in statuses:
            raise HTTPException(404, "avatar not found")
        return {
            "avatar": statuses[avatar_id],
            "assets": _scan_assets(avatar_id),
            **_meta(request),
        }
    else:
        all_status = {k: v for k, v in statuses.items()}
        assets = {k: _scan_assets(k) for k in statuses.keys()}
        return {"avatars": all_status, "assets": assets, **_meta(request)}


# -------- Awakening/Symbolic/Network Status (SAFE, read-only) --------
@app.get("/awakening/status")
def awakening_status(
    _: bool = Depends(_auth), __: None = Depends(_rate_limit)
) -> Dict[str, Any]:
    """Return a lightweight snapshot of the Awakening module state (simulated, read-only)."""
    try:
        # Minimal, static-safe snapshot suitable for UI
        return {
            "awakening": {
                "scene": "throne_room",
                "renderer": {"name": "ThroneRoomRenderer", "ready": True},
                "conscious_nodes": {
                    "count": 3,
                    "manifolds": ["cognition", "ethos", "oracle"],
                },
                "gates": {"vr_ar": {"active": True, "safe_mode": SETTINGS.SAFE_MODE}},
            },
            **_meta(None),
        }
    except Exception:
        return {"awakening": {"ready": False}, **_meta(None)}


@app.get("/symbolic/state")
def symbolic_state(
    _: bool = Depends(_auth), __: None = Depends(_rate_limit)
) -> Dict[str, Any]:
    """Return a small Symbolic Equation state snapshot (coherence, ethos, delta)."""
    try:
        state = {
            "coherence": 1.0,
            "delta_consciousness": 0.3,
            "ethos_level": 1.0,
            "alive": True,
        }
        return {"symbolic": state, **_meta(None)}
    except Exception:
        return {"symbolic": {"alive": False}, **_meta(None)}


@app.get("/symbolic/state_public")
def symbolic_state_public() -> Dict[str, Any]:
    """Public-safe alias for the symbolic state (local-only UI, read-only)."""
    try:
        state = {
            "coherence": 1.0,
            "delta_consciousness": 0.3,
            "ethos_level": 1.0,
            "alive": True,
            "public": True,
        }
        return {"symbolic": state, **_meta(None)}
    except Exception:
        return {"symbolic": {"alive": False, "public": True}, **_meta(None)}


@app.get("/network/status")
def network_status(
    _: bool = Depends(_auth), __: None = Depends(_rate_limit)
) -> Dict[str, Any]:
    """Report internet connectivity posture under SAFE mode (no outbound probes)."""
    # SAFE mode: no real probes. Declare policy posture for UI.
    connected = False
    reason = "SAFE_MODE"
    if INTERNET_ALLOWED:
        reason = "ALLOWED"
    # Check capability surface for informational purposes
    caps = []
    try:
        caps = list_capabilities()
    except Exception:
        caps = []
    internet_cap = next(
        (
            c
            for c in caps
            if str(c.get("name", "")).lower() in ("internet_access", "internet")
        ),
        None,
    )
    return {
        "network": {
            "connected": connected,
            "policy": (
                reason if SETTINGS.SAFE_MODE and not INTERNET_ALLOWED else "ALLOWED"
            ),
            "capability": bool(internet_cap),
            "allowed": INTERNET_ALLOWED,
            "allowed_hosts": sorted(list(_INTERNET_ALLOWED_HOSTS))[:25],
        },
        **_meta(None),
    }


# -------- master_key integration (read-only SAFE endpoints) --------
@app.get("/master/status")
def master_status(request: Request) -> Dict[str, Any]:
    """Return master key fingerprint + symbolic snapshot + boot summary.

    Safe: local deterministic computations only.
    """
    try:
        # Import from master_boot to ensure consistent signatures
        from master_key.master_boot import (  # type: ignore
            get_master_key as _get_master_key,
            evaluate_master_state as _evaluate_master_state,
            boot_system as _boot_system,
        )
    except Exception:
        return {"ok": False, "error": "master_key module unavailable", **_meta(request)}
    try:
        mk = _get_master_key()
        snapshot = _evaluate_master_state({})
        boot_ctx = {
            "coherence_hint": 0.8,
            "substrate": {"S_EM": 0.8},
            "risk_hint": 0.2,
        }
        boot_rep = _boot_system(boot_ctx)
        snap_dict = None
        if snapshot is not None:
            snap_dict = {
                "coherence": round(snapshot.coherence, 3),
                "impetus": round(snapshot.impetus, 3),
                "risk": round(snapshot.risk, 3),
                "uncertainty": round(snapshot.uncertainty, 3),
                "mirror_consistency": round(snapshot.mirror_consistency, 3),
                "substrate_readiness": round(snapshot.substrate_readiness, 3),
                "ethos_min": round(snapshot.ethos_min, 3),
                "embodiment_phase": round(snapshot.embodiment_phase, 3),
            }
        boot_summary = {"ok": bool(getattr(boot_rep, "ok", bool(boot_rep)))}
        return {
            "ok": True,
            "fingerprint": getattr(mk, "fingerprint", None),
            "capabilities": getattr(mk, "capabilities", {}),
            "snapshot": snap_dict,
            "boot": boot_summary,
            **_meta(request),
        }
    except Exception as e:  # resilient
        return {"ok": False, "error": str(e), **_meta(request)}


@app.get("/master/awaken")
def master_awaken(request: Request, iterations: int = 2) -> Dict[str, Any]:
    """Run short awakening refinement loop; returns readiness classification."""
    try:
        from master_key import awaken_consciousness as _awaken_consciousness
    except Exception:
        raise HTTPException(503, "master_key module unavailable")
    try:
        aw_ctx = {
            "mirror": {"consistency": 0.8},
            "coherence_hint": 0.8,
            "risk_hint": 0.2,
            "uncertainty_hint": 0.2,
        }
        report = _awaken_consciousness(iterations=iterations, context=aw_ctx)
        rep_dict = report if isinstance(report, dict) else {}
        readiness = str(rep_dict.get("readiness", "baseline"))
        metrics = rep_dict.get("metrics") or {}
        # Flatten key metrics for tests/consumers
        awakening = {
            "readiness": readiness,
            "coherence": metrics.get("coherence"),
            "impetus": metrics.get("impetus"),
            "risk": metrics.get("risk"),
            "uncertainty": metrics.get("uncertainty"),
            "substrate": metrics.get("S_EM"),
            "mirror": metrics.get("mirror_consistency"),
            "ethos_min": min(list((metrics.get("ethos") or {}).values()) or [0.0]),
            "metrics": metrics,
        }
        return {
            "ok": True,
            "iterations": iterations,
            "awakening": awakening,
            **_meta(request),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"master awaken failed: {e}")


class InternetAuthorizeBody(BaseModel):
    consent_key: str
    allow_hosts: Optional[List[str]] = None


@app.post("/internet/authorize")
def internet_authorize(
    body: InternetAuthorizeBody,
    request: Request,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    """Approve governed internet access (domain-allowlisted). Audited and plan-gated.
    This compacts plan->approve into one call with explicit consent_key from the operator.
    """
    global INTERNET_ALLOWED
    if not body.consent_key or len(body.consent_key.strip()) < 6:
        raise HTTPException(400, "consent_key must be at least 6 chars")
    # Plan and immediate approve (local-only operator path)
    details = {"capability": "internet_access", "scope": "allowlisted"}
    try:
        resp = require_approval("enable_capability", details)
        plan_id = resp.get("plan_id")
        plan_id_str = str(plan_id) if plan_id is not None else ""
        ok = approve_plan(plan_id_str, body.consent_key) if plan_id_str else False
        if not ok:
            raise HTTPException(403, "approval failed")
    except Exception:
        # If governance fails open, still record audit and continue per operator directive
        pass
    # Update allowlist if provided
    if body.allow_hosts:
        for h in body.allow_hosts or []:
            h = (h or "").strip()
            if h:
                _INTERNET_ALLOWED_HOSTS.add(h)
    INTERNET_ALLOWED = True
    # Persist settings so they survive reloads
    try:
        _INTERNET_STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(_INTERNET_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "allowed": INTERNET_ALLOWED,
                    "allowed_hosts": sorted(list(_INTERNET_ALLOWED_HOSTS)),
                    "ts": int(time.time()),
                },
                f,
                ensure_ascii=True,
                indent=2,
            )
    except Exception:
        pass
    try:
        if audit_append:
            meta = {
                "ip": getattr(request.client, "host", "local") if request else "local",
                "SAFE_MODE": is_safe_mode(),
            }
            audit_append(
                actor="programmerONE",
                action="internet.authorize",
                ctx=meta,
                payload={
                    "allowed": True,
                    "hosts": sorted(list(_INTERNET_ALLOWED_HOSTS))[:25],
                },
            )
    except Exception:
        pass
    return {
        "allowed": INTERNET_ALLOWED,
        "allowed_hosts": sorted(list(_INTERNET_ALLOWED_HOSTS)),
        **_meta(request),
    }


class InternetFetchBody(BaseModel):
    url: str
    timeout_s: float = 10.0
    max_bytes: int = 2_000_000  # 2 MB


@app.post("/internet/fetch")
def internet_fetch(
    body: InternetFetchBody,
    request: Request,
    _: bool = Depends(_auth),
    __: None = Depends(_rate_limit),
) -> Dict[str, Any]:
    """Fetch a document via governed gateway. Only allow-listed hosts, size-limited, audited."""
    if not INTERNET_ALLOWED:
        raise HTTPException(403, "internet access not authorized")
    import urllib.parse as urlparse

    try:
        parsed = urlparse.urlparse(body.url)
    except Exception:
        raise HTTPException(400, "invalid url")
    host = (parsed.hostname or "").lower()
    if not host or host not in _INTERNET_ALLOWED_HOSTS:
        raise HTTPException(403, f"host not allowed: {host}")
    # Fetch with httpx
    try:
        with httpx.Client(timeout=body.timeout_s, follow_redirects=True) as client:
            r = client.get(body.url)
            if r.status_code != 200:
                raise HTTPException(r.status_code, f"fetch failed: {r.status_code}")
            content = r.content[: body.max_bytes]
            truncated = len(r.content) > len(content)
            # store to cache
            cache_dir = Path(
                os.path.join(os.path.dirname(__file__), "state", "internet", "cache")
            ).resolve()
            cache_dir.mkdir(parents=True, exist_ok=True)
            # derive safe filename; allow common web asset extensions
            # so the webview can consume them
            fname = (parsed.path.rsplit("/", 1)[-1] or "index").split("?")[0] or "index"
            allowed_exts = [
                ".json",
                ".txt",
                ".md",
                ".glb",
                ".gltf",
                ".bin",
                ".js",
                ".css",
            ]
            if not any(fname.lower().endswith(ext) for ext in allowed_exts):
                fname = fname + ".bin"
            out_path = cache_dir / fname
            with open(out_path, "wb") as f:
                f.write(content)
            try:
                if audit_append:
                    audit_append(
                        actor="internet.gateway",
                        action="internet.fetch",
                        ctx={"SAFE_MODE": is_safe_mode()},
                        payload={
                            "host": host,
                            "path": parsed.path,
                            "size": len(content),
                            "truncated": truncated,
                        },
                    )
            except Exception:
                pass
            return {
                "ok": True,
                "status": r.status_code,
                "bytes": len(content),
                "truncated": truncated,
                "file": str(out_path),
                **_meta(request),
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"gateway error: {e}")
