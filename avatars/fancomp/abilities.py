from __future__ import annotations

import asyncio
import base64
from typing import Any, AsyncIterator, Dict, Optional

from utils.audit import audit_ndjson

from avatars.orchestrator.api import AvatarIntent, ModuleAdapter
from fancompfoundation import services


def _ensure_artist(artist_id: Optional[str], artist_name: Optional[str]) -> str:
    if artist_id:
        artist = services.get_artist(artist_id)
        if artist is not None:
            return artist.id
    if not artist_name:
        raise ValueError("artist_name required when artist_id missing")
    artist = services.create_artist(artist_name)
    return artist.id


def _decode_upload(args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    blob = args.get("file_b64")
    if not blob:
        return None
    try:
        payload = base64.b64decode(blob)
    except Exception:
        raise ValueError("invalid file_b64")
    filename = args.get("filename") or "upload.bin"
    return {"bytes": payload, "filename": filename}


def _ability_explain_state(_: AvatarIntent) -> Dict[str, Any]:
    metrics = services.metrics()
    content_count = metrics["content"]
    artist_count = metrics["artists"]
    revenue_ser = metrics["revenue_cents"] / 100.0
    pool_ser = metrics["pool_balance_cents"] / 100.0
    speech = (
        f"FanComp is tracking {content_count} works from {artist_count} artists. "
        f"Paper revenue totals {revenue_ser:.2f} SER with pool balances at {pool_ser:.2f}."
    )
    return {
        "speech": speech,
        "widgets": services.dashboard()["widgets"],
    }


def _ability_upload_ip(intent: AvatarIntent) -> Dict[str, Any]:
    args = intent.args
    artist_id = args.get("artist_id")
    artist_name = args.get("artist_name")
    resolved_artist_id = _ensure_artist(artist_id, artist_name)
    upload_payload = _decode_upload(args) or {"bytes": None, "filename": "asset.bin"}
    content = services.ingest_content(
        artist_id=resolved_artist_id,
        title=args.get("title", "Untitled"),
        price_cents=int(args.get("price_cents", 0)),
        kind=args.get("kind", "media"),
        license_terms=args.get("license_terms", "non-exclusive, revocable"),
        metadata=args.get("metadata") or {},
        file_bytes=upload_payload["bytes"],
        filename=upload_payload["filename"],
        percent_alloc=float(args.get("percent_alloc", 0.0)),
    )
    services.record_purchase(content.id, buyer_id=resolved_artist_id, amount_cents=0)
    return {
    "speech": f"Stored {content.title} with hash {content.hash[:8]}... and refreshed the fancomp console.",
        "widgets": services.dashboard()["widgets"],
        "content": content.to_dict(),
    }


def _ability_join_pool(intent: AvatarIntent) -> Dict[str, Any]:
    args = intent.args
    content_id = args.get("content_id")
    if not content_id:
        raise ValueError("content_id required")
    buyer_id = args.get("buyer_id") or intent.session_id
    amount_cents = int(args.get("amount_cents", 100))
    tx = services.record_purchase(content_id, buyer_id, amount_cents, args.get("affiliate_code"))
    pool_info = services.pool_state(content_id)
    pool_payload = pool_info.get("pool")
    if isinstance(pool_payload, dict) and pool_payload:
        balance = float(pool_payload.get("balance_cents", 0)) / 100.0
        speech = f"Registered your entry for content {content_id}. Pool balance is {balance:.2f} SER paper."
    else:
        speech = f"Registered your entry for content {content_id}. This content has no active pool yet."
    return {
        "speech": speech,
        "transaction": tx.to_dict(),
        "widgets": services.dashboard()["widgets"],
        "pool": pool_info,
    }


def _route_intent(payload: AvatarIntent) -> Dict[str, Any]:
    intent = payload.intent
    if intent is None and payload.text:
        lowered = payload.text.lower()
        if "explain" in lowered:
            intent = "explain_state"
        elif "upload" in lowered:
            intent = "upload_ip"
        elif "join" in lowered:
            intent = "join_pool"
    intent = intent or "explain_state"
    if intent == "explain_state":
        return _ability_explain_state(payload)
    if intent == "upload_ip":
        return _ability_upload_ip(payload)
    if intent == "join_pool":
        return _ability_join_pool(payload)
    raise ValueError(f"unsupported intent: {intent}")


async def _stream_updates(payload: AvatarIntent) -> AsyncIterator[Dict[str, Any]]:
    # Simple heartbeat stream that yields current metrics once per request.
    yield {"event": "metrics", "data": services.metrics()}
    await asyncio.sleep(0)


def handle_intent(payload: AvatarIntent) -> Dict[str, Any]:
    try:
        response = _route_intent(payload)
    except ValueError as exc:
        return {"speech": str(exc), "error": str(exc)}
    audit_ndjson(
        "fancomp_avatar_intent",
        intent=payload.intent or payload.text,
        session_id=payload.session_id,
        avatar_id="fancomp",
    )
    return response


def get_state() -> Dict[str, Any]:
    return dict(services.metrics())


def get_dashboard() -> Dict[str, Any]:
    return services.dashboard()


def get_module_adapter() -> ModuleAdapter:
    return ModuleAdapter(
        avatar_id="fancomp",
        handle_intent=handle_intent,
        fetch_state=get_state,
        fetch_dashboard=get_dashboard,
        stream_events=_stream_updates,
    )
