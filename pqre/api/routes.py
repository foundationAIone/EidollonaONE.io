from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator

from ai_core.probabilistic_rendering_engine import (
    ProbabilisticRenderingEngine,
    RenderRequest,
)
from ai_core.quantum_core.quantum_probabilistic_inference import run_inference
from security.deps import require_token
from utils.audit import audit_ndjson

router = APIRouter()

_ENGINE = ProbabilisticRenderingEngine(name="PQRE")


class RenderIn(BaseModel):
    signals: Dict[str, Any] = Field(default_factory=dict)
    features: Optional[Dict[str, float]] = None
    nx: int = 32
    ny: int = 32
    sharpness: float = 0.6
    noise: float = 0.1
    seed: Optional[int] = None
    include_inference: bool = True
    conservatism: float = Field(0.45, ge=0.0, le=1.0)
    ethos_bias: float = Field(0.55, ge=0.0, le=1.0)

    @validator("nx", "ny")
    def _check_dims(cls, value: int) -> int:
        if value <= 4 or value > 256:
            raise ValueError("nx/ny must be within 5..256 for SAFE simulations")
        return value

    @validator("sharpness", "noise")
    def _clamp_params(cls, value: float) -> float:
        if value < 0.0 or value > 1.0:
            raise ValueError("sharpness/noise must be within [0, 1]")
        return value


@router.get("/pqre/ping")
def ping(_: str = Depends(require_token)) -> Dict[str, Any]:
    return {"ok": True, "ts": time.time(), "engine": _ENGINE.name}


@router.post("/pqre/render")
def render(req: RenderIn, token: str = Depends(require_token)) -> Dict[str, Any]:
    render_req = RenderRequest(
        signals=req.signals,
        features=req.features,
        nx=req.nx,
        ny=req.ny,
        sharpness=req.sharpness,
        noise=req.noise,
        seed=req.seed,
    )
    try:
        result = _ENGINE.render(render_req)
    except Exception as exc:  # pragma: no cover - defensive guard
        audit_ndjson("pqre_render_error", token=token, error=str(exc))
        raise HTTPException(status_code=500, detail="render_failed") from exc

    payload: Dict[str, Any] = {
        "field": asdict(result.field),
        "strategies": [asdict(strategy) for strategy in result.strategies],
        "recommendation": result.rec,
    }

    inference_payload: Optional[Dict[str, Any]] = None
    if req.include_inference:
        report = run_inference(
            result.field,
            result.strategies,
            conservatism=req.conservatism,
            ethos_bias=req.ethos_bias,
        )
        inference_payload = {
            "refined_field": report.refined_field,
            "hotspots": report.hotspots,
            "adjustments": [asdict(strategy) for strategy in report.adjustments],
            "summary": report.summary,
        }
        payload["inference"] = inference_payload

    audit_ndjson(
        "pqre_render_api",
        token=token,
        params={
            "nx": req.nx,
            "ny": req.ny,
            "sharpness": req.sharpness,
            "noise": req.noise,
            "include_inference": req.include_inference,
        },
        signals={k: v for k, v in req.signals.items()},
        recommendation=result.rec,
        inference_summary=(inference_payload or {}).get("summary"),
    )
    return payload


__all__ = ["router"]
