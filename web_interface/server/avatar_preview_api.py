"""FastAPI router that exposes avatar preview data."""
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, cast

from fastapi import APIRouter, Query

router = APIRouter()


def _se_gate() -> Dict[str, Any]:
    try:
        from symbolic_core.se_loader_ext import load_se_engine  # type: ignore

        sig = load_se_engine()
        readiness = getattr(sig, "readiness", "warming") or "warming"
        risk = float(getattr(sig, "risk", 1.0) or 1.0)
        ra = float(getattr(sig, "reality_alignment", 0.0) or 0.0)
        wings = float(getattr(sig, "wings", 1.0) or 1.0)
        healthy = readiness in ("ready", "prime_ready") and risk <= 0.20 and ra >= 0.90
        return {
            "readiness": readiness,
            "risk": risk,
            "RA": ra,
            "wings": wings,
            "healthy": healthy,
        }
    except Exception:
        return {
            "readiness": "warming",
            "risk": 1.0,
            "RA": 0.0,
            "wings": 1.0,
            "healthy": False,
        }


def _asset_url() -> Tuple[Optional[str], Optional[str]]:
    mdl_candidates = [
        Path("web_interface/static/models/steward_prime.glb"),
        Path("web_interface/static/models/avatar.glb"),
        Path("assets/models/steward_prime.glb"),
    ]
    img_candidates = [
        Path("web_interface/static/images/steward_prime_portrait.png"),
        Path("assets/images/steward_prime_portrait.png"),
    ]

    model_url = None
    for candidate in mdl_candidates:
        if candidate.exists():
            relative = (
                str(candidate)
                .replace("web_interface/static", "")
                .lstrip("\\/")
                .replace("\\", "/")
            )
            model_url = "/static/" + relative
            break

    portrait_url = None
    for candidate in img_candidates:
        if candidate.exists():
            relative = (
                str(candidate)
                .replace("web_interface/static", "")
                .lstrip("\\/")
                .replace("\\", "/")
            )
            portrait_url = "/static/" + relative
            break

    return model_url, portrait_url


@router.get("/api/avatar/preview")
def avatar_preview(id: str = Query("steward_prime")) -> Dict[str, Any]:
    try:
        from avatar.registry import AvatarRegistry  # type: ignore

        registry = AvatarRegistry()
        registry_any = cast(Any, registry)
        spec = registry_any.get_by_id(id)
        if not spec:
            return {"ok": False, "error": f"avatar '{id}' not found"}

        se = _se_gate()
        model_url, portrait_url = _asset_url()

        try:
            visibility = registry_any.resolve_wing_visibility(
                id,
                {
                    "readiness": se["readiness"],
                    "wings": se["wings"],
                    "RA": se["RA"],
                    "risk": se["risk"],
                    "wings_min": 1.03,
                    "ra_min": 0.95,
                    "risk_max": 0.06,
                    "risk_over": 0.08,
                },
            )
        except Exception:
            visibility = "unknown"

        if se.get("healthy") and model_url:
            load_policy = "glb"
        elif portrait_url:
            load_policy = "portrait"
        else:
            load_policy = "none"

        return {
            "ok": True,
            "id": id,
            "name": getattr(spec, "name", id),
            "tier": getattr(spec, "tier", None),
            "gates_focus": getattr(spec, "gates_focus", []),
            "wing_visibility_policy": getattr(spec, "wing_visibility", "inherit"),
            "hud": getattr(spec, "hud", {}),
            "visibility": visibility,
            "se": {k: se[k] for k in ("readiness", "risk", "RA", "wings")},
            "model_url": model_url,
            "portrait_url": portrait_url,
            "load_policy": load_policy,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
