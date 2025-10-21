from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Form, HTTPException

from security.deps import require_token

from . import services

router = APIRouter(prefix="/v1/serveit", tags=["serveit"])


@router.post("/request")
def create_request(
    user_id: str = Form(...),
    service_type: str = Form(...),
    description: str = Form(""),
    lat: float = Form(0.0),
    lon: float = Form(0.0),
    token: str = Depends(require_token),
) -> Dict[str, Any]:
    services.ensure_service_type(service_type)
    request = services.create_request(user_id, service_type, description, lat, lon)
    return {"ok": True, "request": request.to_dict()}


@router.get("/quotes")
def list_quotes(request_id: str, token: str = Depends(require_token)) -> Dict[str, Any]:
    quotes = [quote.to_dict() for quote in services.quotes_for_request(request_id)]
    return {"ok": True, "quotes": quotes}


@router.post("/quote")
def submit_quote(
    request_id: str = Form(...),
    provider_id: str = Form(...),
    price_cents: int = Form(...),
    eta_hours: float = Form(1.0),
    token: str = Depends(require_token),
) -> Dict[str, Any]:
    quote = services.add_quote(request_id, provider_id, int(price_cents), float(eta_hours))
    return {"ok": True, "quote": quote.to_dict()}


@router.post("/book")
def book_quote(quote_id: str = Form(...), token: str = Depends(require_token)) -> Dict[str, Any]:
    booking = services.create_booking(quote_id)
    return {"ok": True, "booking": booking.to_dict()}


@router.post("/complete")
def complete_booking(
    booking_id: str = Form(...),
    proof: Optional[str] = Form(None),
    token: str = Depends(require_token),
) -> Dict[str, Any]:
    try:
        booking = services.complete_booking(booking_id, proof)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True, "booking": booking.to_dict()}


@router.post("/payout_paper")
def payout_paper(
    booking_id: str = Form(...),
    account: str = Form(...),
    amount_cents: int = Form(...),
    token: str = Depends(require_token),
) -> Dict[str, Any]:
    receipt = services.payout_paper(booking_id, account, int(amount_cents))
    return {"ok": True, "receipt": receipt}


@router.get("/hoa/{hoa_id}")
def hoa_view(hoa_id: str, token: str = Depends(require_token)) -> Dict[str, Any]:
    return {"ok": True, "hoa": services.hoa_summary(hoa_id)}


@router.get("/metrics")
def module_metrics(token: str = Depends(require_token)) -> Dict[str, Any]:
    return {"ok": True, "metrics": services.metrics()}


@router.get("/dashboard")
def module_dashboard(token: str = Depends(require_token)) -> Dict[str, Any]:
    return {"ok": True, "dashboard": services.dashboard()}
