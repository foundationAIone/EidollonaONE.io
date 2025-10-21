from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pathlib import Path
from typing import Dict, Any, Optional
import os
import time

_append_event: Optional[object]
try:
    from common.audit_chain import append_event as _append_event  # type: ignore
except Exception:
    _append_event = None  # type: ignore


def _audit(**kwargs: Any) -> str:
    try:
        if _append_event:
            return _append_event(**kwargs)  # type: ignore[misc]
    except Exception:
        pass
    return "noop"


try:
    # SAFE intake guard
    from web_planning.backend.guardian.ai_firewall import guard_intake as _guard_in  # type: ignore
except Exception:

    def _guard_in(_: str):
        return True, {}


try:
    # Avatar API shims (implemented in avatar/interface/avatar_api.py)
    from avatar.interface.avatar_api import load_avatar, pose_avatar, animate_avatar, export_avatar  # type: ignore
except Exception:  # pragma: no cover
    load_avatar = pose_avatar = animate_avatar = export_avatar = None  # type: ignore

try:
    from avatar.reactive_layer import generate_directive as _generate_directive  # type: ignore
    from avatar.reactive_layer import directive_summary as _directive_summary  # type: ignore
except Exception:  # pragma: no cover
    _generate_directive = None  # type: ignore
    _directive_summary = None  # type: ignore


router = APIRouter(prefix="/avatar", tags=["avatar"])
STATE_DIR = Path(
    os.path.join(os.path.dirname(__file__), "..", "state", "avatar")
).resolve()
ART_DIR = STATE_DIR / "artifacts"
CFG_PATH = Path("avatar/config/default_avatar_config.yaml").resolve()

_SPEC = {
    "spec_version": 1,
    "caps": {
        "build": True,
        "pose": True,
        "animate": True,
        "export": True,
        "headless": True,
    },
}


def _ok_guard(text: str) -> None:
    ok, meta = _guard_in(text)
    if not ok:
        raise HTTPException(400, f"avatar_guard_blocked:{(meta or {}).get('reason')}")


def _meta(request: Request) -> Dict[str, Any]:
    return {
        "request_id": getattr(getattr(request, "state", None), "correlation_id", None)
    }


def _urls_for_run(run_id: str) -> Dict[str, Any]:
    """Return file names and served URLs for a given artifact run."""
    outdir = ART_DIR / run_id
    files = sorted([p.name for p in outdir.glob("*") if p.is_file()])
    urls = [f"/assets/artifacts/{run_id}/{name}" for name in files]
    return {"files": files, "urls": urls}


@router.get("/spec")
def spec(request: Request) -> Dict[str, Any]:
    return {**_SPEC, **_meta(request)}


@router.post("/build")
def build_avatar(request: Request) -> Dict[str, Any]:
    _ok_guard("build avatar")
    run_id = str(int(time.time()))
    try:
        ART_DIR.mkdir(parents=True, exist_ok=True)
        outdir = ART_DIR / run_id
        outdir.mkdir(parents=True, exist_ok=True)
        if load_avatar is None or export_avatar is None:
            raise RuntimeError("avatar_api not available")
        av = load_avatar(config_path=str(CFG_PATH))
        export_avatar(avatar=av, out_dir=str(outdir), kind="thumbnail")
        _audit(
            actor="avatar",
            action="build",
            ctx={"run_id": run_id},
            payload={"cfg": str(CFG_PATH)},
        )
        return {"ok": True, "run_id": run_id, **_urls_for_run(run_id), **_meta(request)}
    except Exception as e:
        _audit(
            actor="avatar",
            action="build_error",
            ctx={"run_id": run_id},
            payload={"err": str(e)},
        )
        raise HTTPException(500, f"avatar_build_error: {e}")


@router.post("/pose")
def pose(request: Request, body: Dict[str, Any]) -> Dict[str, Any]:
    _ok_guard("pose avatar")
    run_id = str(body.get("run_id") or int(time.time()))
    pose_name = str(body.get("pose") or "neutral")
    try:
        outdir = ART_DIR / run_id
        outdir.mkdir(parents=True, exist_ok=True)
        if pose_avatar is None:
            raise RuntimeError("avatar_api not available")
        pose_avatar(pose=pose_name, out_dir=str(outdir))
        _audit(
            actor="avatar",
            action="pose",
            ctx={"run_id": run_id},
            payload={"pose": pose_name},
        )
        return {
            "ok": True,
            "run_id": run_id,
            "pose": pose_name,
            **_urls_for_run(run_id),
            **_meta(request),
        }
    except Exception as e:
        _audit(
            actor="avatar",
            action="pose_error",
            ctx={"run_id": run_id},
            payload={"err": str(e)},
        )
        raise HTTPException(500, f"avatar_pose_error: {e}")


@router.post("/animate")
def animate(request: Request, body: Dict[str, Any]) -> Dict[str, Any]:
    _ok_guard("animate avatar")
    run_id = str(body.get("run_id") or int(time.time()))
    clip = str(body.get("clip") or "idle")
    seconds = int(body.get("seconds") or 2)
    try:
        outdir = ART_DIR / run_id
        outdir.mkdir(parents=True, exist_ok=True)
        if animate_avatar is None:
            raise RuntimeError("avatar_api not available")
        animate_avatar(clip=clip, seconds=seconds, out_dir=str(outdir))
        _audit(
            actor="avatar",
            action="animate",
            ctx={"run_id": run_id},
            payload={"clip": clip, "seconds": seconds},
        )
        return {
            "ok": True,
            "run_id": run_id,
            "clip": clip,
            "seconds": seconds,
            **_urls_for_run(run_id),
            **_meta(request),
        }
    except Exception as e:
        _audit(
            actor="avatar",
            action="animate_error",
            ctx={"run_id": run_id},
            payload={"err": str(e)},
        )
        raise HTTPException(500, f"avatar_animate_error: {e}")


@router.post("/reactive")
def reactive(request: Request, body: Dict[str, Any]) -> Dict[str, Any]:
    _ok_guard("avatar reactive")
    if _generate_directive is None or _directive_summary is None:
        raise HTTPException(503, "avatar_reactive_unavailable")

    signals = dict(body.get("signals") or {})
    features = body.get("features")
    seed = body.get("seed")
    try:
        directive = _generate_directive(
            signals=signals,
            features=features if isinstance(features, dict) else None,
            seed=int(seed) if seed is not None else None,
        )
    except Exception as e:
        _audit(actor="avatar", action="reactive_error", payload={"err": str(e)})
        raise HTTPException(500, f"avatar_reactive_error: {e}")

    summary = _directive_summary(directive)
    payload = {
        "signals": signals,
        "features": features or {},
        "directive": directive.as_dict(),
        "summary": summary,
    }
    _audit(actor="avatar", action="reactive", payload=payload)
    return {"ok": True, **payload, **_meta(request)}


@router.get("/artifacts/{run_id}")
def artifacts(run_id: str, request: Request) -> Dict[str, Any]:
    outdir = ART_DIR / run_id
    if not outdir.exists():
        raise HTTPException(404, "not_found")
    info = _urls_for_run(run_id)
    return {"ok": True, "run_id": run_id, **info, **_meta(request)}
