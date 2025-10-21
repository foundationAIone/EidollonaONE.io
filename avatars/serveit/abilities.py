from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional

from utils.audit import audit_ndjson

from avatars.orchestrator.api import AvatarIntent, ModuleAdapter
from serve_it_app import services


def _ensure_user(user_id: Optional[str], role: str) -> str:
    if user_id:
        existing = services.get_user(user_id)
        if existing is not None:
            return existing.id
    user = services.create_user(role)
    return user.id


def _ensure_providers(service_type: str, count: int = 1) -> List[str]:
    providers = services.list_providers()
    if providers:
        return [provider.id for provider in providers]
    provider_user = services.create_user("provider")
    provider = services.register_provider(provider_user.id, [service_type])
    return [provider.id]


def _ability_explain_state(_: AvatarIntent) -> Dict[str, Any]:
    metrics = services.metrics()
    speech = (
        f"Serve-it handled {metrics['requests']} requests with {metrics['bookings']} bookings. "
        f"Completion rate is {(metrics['completed'] / metrics['bookings'] * 100) if metrics['bookings'] else 0:.1f}% "
        f"and average rating is {metrics['avg_rating']:.1f}."
    )
    return {"speech": speech, "widgets": services.dashboard()["widgets"]}


def _ability_quote_task(intent: AvatarIntent) -> Dict[str, Any]:
    args = intent.args
    service_type = args.get("service_type", "general")
    services.ensure_service_type(service_type)
    user_id = _ensure_user(args.get("user_id"), role="receiver")
    request = services.create_request(
        user_id,
        service_type,
        args.get("description", ""),
        float(args.get("lat", 0.0)),
        float(args.get("lon", 0.0)),
    )
    provider_ids = _ensure_providers(service_type)
    quotes = []
    for provider_id in provider_ids[:3]:
        quotes.append(
            services.add_quote(
                request.id,
                provider_id,
                int(args.get("price_cents", 2500)),
                float(args.get("eta_hours", 1.0)),
            ).to_dict()
        )
    return {
        "speech": f"Generated {len(quotes)} quote(s) for your request.",
        "request": request.to_dict(),
        "quotes": quotes,
        "widgets": services.dashboard()["widgets"],
    }


def _ability_accept_task(intent: AvatarIntent) -> Dict[str, Any]:
    args = intent.args
    quote_id = args.get("quote_id")
    if not quote_id:
        request_id = args.get("request_id")
        if not request_id:
            raise ValueError("quote_id or request_id required")
        quotes = services.quotes_for_request(request_id)
        if not quotes:
            raise ValueError("no quotes available for request")
        quote_id = quotes[0].id
    booking = services.create_booking(quote_id)
    return {
        "speech": f"Booked quote {quote_id}; provider notified.",
        "booking": booking.to_dict(),
        "widgets": services.dashboard()["widgets"],
    }


def _ability_payout_paper(intent: AvatarIntent) -> Dict[str, Any]:
    args = intent.args
    booking_id = args.get("booking_id")
    if not booking_id:
        raise ValueError("booking_id required")
    account = args.get("account") or "paper-ledger"
    amount_cents = int(args.get("amount_cents", 2500))
    receipt = services.payout_paper(booking_id, account, amount_cents)
    return {
        "speech": f"Filed paper payout of {amount_cents/100.0:.2f} SER equivalent to {account}.",
        "receipt": receipt,
    }


def _route_intent(payload: AvatarIntent) -> Dict[str, Any]:
    intent = payload.intent
    if intent is None and payload.text:
        lowered = payload.text.lower()
        if "quote" in lowered or "task" in lowered:
            intent = "quote_task"
        elif "accept" in lowered or "book" in lowered:
            intent = "accept_task"
        elif "pay" in lowered or "payout" in lowered:
            intent = "payout_paper"
        else:
            intent = "explain_state"
    intent = intent or "explain_state"
    if intent == "explain_state":
        return _ability_explain_state(payload)
    if intent == "quote_task":
        return _ability_quote_task(payload)
    if intent == "accept_task":
        return _ability_accept_task(payload)
    if intent == "payout_paper":
        return _ability_payout_paper(payload)
    raise ValueError(f"unsupported intent: {intent}")


async def _stream_updates(_: AvatarIntent) -> AsyncIterator[Dict[str, Any]]:
    yield {"event": "metrics", "data": services.metrics()}
    await asyncio.sleep(0)


def handle_intent(payload: AvatarIntent) -> Dict[str, Any]:
    try:
        response = _route_intent(payload)
    except ValueError as exc:
        return {"speech": str(exc), "error": str(exc)}
    audit_ndjson(
        "serveit_avatar_intent",
        intent=payload.intent or payload.text,
        session_id=payload.session_id,
        avatar_id="serveit",
    )
    return response


def get_state() -> Dict[str, Any]:
    return dict(services.metrics())


def get_dashboard() -> Dict[str, Any]:
    return services.dashboard()


def get_module_adapter() -> ModuleAdapter:
    return ModuleAdapter(
        avatar_id="serveit",
        handle_intent=handle_intent,
        fetch_state=get_state,
        fetch_dashboard=get_dashboard,
        stream_events=_stream_updates,
    )
