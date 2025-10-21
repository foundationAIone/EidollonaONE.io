from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from security.deps import require_token

from . import compliance, services

router = APIRouter(prefix="/v1/fancomp", tags=["fancomp"])


@router.post("/artist/create")
def create_artist(name: str = Form(...), payout_acct: Optional[str] = Form(None), token: str = Depends(require_token)) -> Dict[str, Any]:
    artist = services.create_artist(name=name, payout_acct=payout_acct)
    return {"ok": True, "artist": artist.to_dict()}


@router.post("/content/upload")
async def upload_content(
    artist_id: str = Form(...),
    title: str = Form(...),
    price_cents: int = Form(...),
    kind: str = Form("media"),
    license_terms: str = Form("non-exclusive, revocable"),
    metadata_json: str = Form("{}"),
    percent_alloc: float = Form(0.0),
    file: Optional[UploadFile] = File(None),
    token: str = Depends(require_token),
) -> Dict[str, Any]:
    try:
        metadata = json.loads(metadata_json) if metadata_json else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"metadata_json invalid: {exc}")
    payload = await file.read() if file is not None else None
    content = services.ingest_content(
        artist_id=artist_id,
        title=title,
        price_cents=int(price_cents),
        kind=kind,
        license_terms=license_terms,
        metadata=metadata,
        file_bytes=payload,
    filename=(file.filename or "asset.bin") if file else "asset.bin",
        percent_alloc=float(percent_alloc),
    )
    return {"ok": True, "content": content.to_dict()}


@router.post("/purchase")
def purchase(
    content_id: str = Form(...),
    buyer_id: str = Form(...),
    amount_cents: int = Form(...),
    affiliate_code: Optional[str] = Form(None),
    token: str = Depends(require_token),
) -> Dict[str, Any]:
    try:
        tx = services.record_purchase(content_id, buyer_id, int(amount_cents), affiliate_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True, "transaction": tx.to_dict()}


@router.get("/pool/state")
def pool_state(content_id: str, token: str = Depends(require_token)) -> Dict[str, Any]:
    return {"ok": True, "state": services.pool_state(content_id)}


@router.post("/pool/draw")
def pool_draw(pool_id: str = Form(...), sample_size: int = Form(1), token: str = Depends(require_token)) -> Dict[str, Any]:
    if not compliance.sweepstakes_enabled():
        raise HTTPException(status_code=403, detail="sweepstakes disabled")
    try:
        draw = services.run_pool_draw(pool_id=pool_id, sample_size=int(sample_size))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "draw": draw.to_dict()}


@router.post("/affiliate/create")
def create_affiliate_link(
    artist_id: Optional[str] = Form(None),
    rate_bps: int = Form(500),
    token: str = Depends(require_token),
) -> Dict[str, Any]:
    link = services.create_affiliate_link(artist_id=artist_id, rate_bps=int(rate_bps))
    return {"ok": True, "link": link.to_dict()}


@router.get("/affiliate/{code}/stats")
def affiliate_stats(code: str, token: str = Depends(require_token)) -> Dict[str, Any]:
    try:
        stats = services.affiliate_stats(code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True, "stats": stats}


@router.get("/metrics")
def module_metrics(token: str = Depends(require_token)) -> Dict[str, Any]:
    return {"ok": True, "metrics": services.metrics()}


@router.get("/dashboard")
def module_dashboard(token: str = Depends(require_token)) -> Dict[str, Any]:
    return {"ok": True, "dashboard": services.dashboard()}
