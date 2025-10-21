from __future__ import annotations

import time
from typing import Dict, List, Optional, TypedDict
from uuid import uuid4

from utils.audit import audit_ndjson

from . import compliance, match, payouts
from .models import (
    Booking,
    JobRequest,
    PaymentStub,
    Provider,
    Quote,
    Rating,
    ServiceType,
    User,
)
from .state import load_state, mutate_state


class MetricsPayload(TypedDict):
    requests: int
    bookings: int
    completed: int
    avg_rating: float


def _to_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _to_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def create_user(role: str) -> User:
    with mutate_state() as state:
        user = User(id=_make_id("user"), role=role)
        state.setdefault("users", []).append(user.to_dict())
        audit_ndjson("serveit_user_create", user_id=user.id, role=role)
        return user


def get_user(user_id: str) -> Optional[User]:
    state = load_state()
    for payload in state.get("users", []):
        if payload.get("id") == user_id:
            return User(**payload)  # type: ignore[arg-type]
    return None


def register_provider(user_id: str, skills: List[str], rating: float = 5.0) -> Provider:
    with mutate_state() as state:
        provider = Provider(id=_make_id("prov"), user_id=user_id, skills=list(skills), rating=rating)
        state.setdefault("providers", []).append(provider.to_dict())
        audit_ndjson("serveit_provider_register", provider_id=provider.id, user_id=user_id, skills=skills)
        return provider


def list_providers() -> List[Provider]:
    state = load_state()
    return [Provider(**payload) for payload in state.get("providers", [])]  # type: ignore[arg-type]


def ensure_service_type(name: str, description: Optional[str] = None) -> ServiceType:
    with mutate_state() as state:
        for payload in state.get("service_types", []):
            if payload.get("name") == name:
                return ServiceType(**payload)  # type: ignore[arg-type]
        svc = ServiceType(id=_make_id("svc"), name=name, description=description)
        state.setdefault("service_types", []).append(svc.to_dict())
        return svc


def create_request(
    user_id: str,
    service_type_id: str,
    description: str,
    lat: float,
    lon: float,
) -> JobRequest:
    with mutate_state() as state:
        request = JobRequest(
            id=_make_id("req"),
            user_id=user_id,
            service_type_id=service_type_id,
            description=description,
            lat=float(lat),
            lon=float(lon),
        )
        state.setdefault("requests", []).append(request.to_dict())
        audit_ndjson("serveit_request", request_id=request.id, service_type_id=service_type_id)
        return request


def list_requests() -> List[JobRequest]:
    state = load_state()
    return [JobRequest(**payload) for payload in state.get("requests", [])]  # type: ignore[arg-type]


def request_by_id(request_id: str) -> Optional[JobRequest]:
    state = load_state()
    for payload in state.get("requests", []):
        if payload.get("id") == request_id:
            return JobRequest(**payload)  # type: ignore[arg-type]
    return None


def add_quote(
    request_id: str,
    provider_id: str,
    price_cents: int,
    eta_hours: float,
) -> Quote:
    with mutate_state() as state:
        quote = Quote(
            id=_make_id("quote"),
            request_id=request_id,
            provider_id=provider_id,
            price_cents=int(price_cents),
            eta_hours=float(eta_hours),
        )
        state.setdefault("quotes", []).append(quote.to_dict())
        audit_ndjson("serveit_quote", quote_id=quote.id, request_id=request_id, provider_id=provider_id)
        return quote


def quotes_for_request(request_id: str) -> List[Quote]:
    state = load_state()
    return [Quote(**payload) for payload in state.get("quotes", []) if payload.get("request_id") == request_id]  # type: ignore[arg-type]


def create_booking(quote_id: str) -> Booking:
    with mutate_state() as state:
        booking = Booking(id=_make_id("booking"), quote_id=quote_id)
        state.setdefault("bookings", []).append(booking.to_dict())
        audit_ndjson("serveit_book", booking_id=booking.id, quote_id=quote_id)
        return booking


def complete_booking(booking_id: str, proof: Optional[str] = None) -> Booking:
    with mutate_state() as state:
        for entry in state.get("bookings", []):
            if entry.get("id") == booking_id:
                entry["status"] = "completed"
                entry["completed_at"] = time.time()
                audit_ndjson("serveit_complete", booking_id=booking_id, proof=proof)
                return Booking(**entry)  # type: ignore[arg-type]
    raise ValueError("booking not found")


def record_rating(booking_id: str, stars: int, comment: Optional[str]) -> Rating:
    with mutate_state() as state:
        rating = Rating(id=_make_id("rating"), booking_id=booking_id, stars=int(stars), comment=comment)
        state.setdefault("ratings", []).append(rating.to_dict())
        audit_ndjson("serveit_rating", booking_id=booking_id, stars=stars)
        return rating


def record_payment_stub(booking_id: str, amount_cents: int, ser_discount_cents: int) -> PaymentStub:
    with mutate_state() as state:
        stub = PaymentStub(
            id=_make_id("payout"),
            booking_id=booking_id,
            amount_cents=int(amount_cents),
            currency="SER-paper",
            ser_discount_cents=int(ser_discount_cents),
        )
        state.setdefault("payments", []).append(stub.to_dict())
        return stub


def top_quotes_for_request(request_payload: JobRequest) -> List[Quote]:
    providers = list_providers()
    scored = match.rank_providers(request_payload.to_dict(), providers)
    quotes: List[Quote] = []
    for provider, score in scored[:3]:
        quotes.append(
            Quote(
                id=_make_id("quote"),
                request_id=request_payload.id,
                provider_id=provider.id,
                price_cents=2500,
                eta_hours=1.5,
            )
        )
    return quotes


def payout_paper(booking_id: str, account: str, amount_cents: int) -> Dict[str, object]:
    stub = record_payment_stub(booking_id, amount_cents, ser_discount_cents=int(amount_cents * 0.1))
    receipt = payouts.payout_paper_ser(booking_id, account, amount_cents)
    receipt.update({"stub": stub.to_dict()})
    return receipt


def hoa_summary(hoa_id: str) -> Dict[str, object]:
    state = load_state()
    bookings = state.get("bookings", [])
    total = len(bookings)
    return {
        "hoa_id": hoa_id,
        "total_bookings": total,
        "revenue_share_bps": 0,
    }


def metrics() -> MetricsPayload:
    state = load_state()
    requests = state.get("requests", [])
    bookings = state.get("bookings", [])
    completed = [entry for entry in bookings if entry.get("status") == "completed"]
    ratings = state.get("ratings", [])
    avg_rating = 0.0
    if ratings:
        total_stars = sum(_to_int(entry.get("stars", 0)) for entry in ratings)
        if len(ratings) > 0:
            avg_rating = total_stars / float(len(ratings))
    return MetricsPayload(
        requests=len(requests),
        bookings=len(bookings),
        completed=len(completed),
        avg_rating=round(avg_rating, 2),
    )


def dashboard() -> Dict[str, object]:
    state = load_state()
    metrics_payload = metrics()
    recent_requests = sorted(
        state.get("requests", []),
        key=lambda item: _to_float(item.get("ts", 0.0)),
        reverse=True,
    )[:5]
    recent_bookings = sorted(
        state.get("bookings", []),
        key=lambda item: _to_float(item.get("ts", 0.0)),
        reverse=True,
    )[:5]
    return {
        "widgets": {
            "kpis": [
                {"name": "Open Requests", "value": metrics_payload["requests"]},
                {"name": "Bookings", "value": metrics_payload["bookings"]},
                {"name": "Completed", "value": metrics_payload["completed"]},
                {"name": "Avg Rating", "value": metrics_payload["avg_rating"]},
            ],
            "tables": [
                {"title": "Recent Requests", "rows": recent_requests},
                {"title": "Recent Bookings", "rows": recent_bookings},
            ],
        },
        "links": {
            "tos": compliance.tos_url(),
            "privacy": compliance.privacy_url(),
        },
    }
