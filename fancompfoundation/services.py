from __future__ import annotations

import json
import os
import random
import secrets
import threading
import time
from hashlib import sha256
from pathlib import Path
from typing import Dict, List, Optional, TypedDict
from uuid import uuid4

from utils.audit import audit_ndjson

from . import compliance
from .models import (
    AffiliateEvent,
    AffiliateLink,
    Artist,
    Content,
    MoneyPool,
    PoolDraw,
    PoolEntry,
    Transaction,
)

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
STATE_PATH = LOG_DIR / "fancomp_state.json"
VAULT_DIR = ROOT / "ip_vault"
LOCK = threading.Lock()


class MetricsPayload(TypedDict):
    artists: int
    content: int
    transactions: int
    revenue_cents: int
    pool_balance_cents: int


def _to_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):  # bool is subclass of int
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


def _default_state() -> Dict[str, List[Dict[str, object]]]:
    return {
        "artists": [],
        "content": [],
        "transactions": [],
        "pools": [],
        "pool_entries": [],
        "draws": [],
        "affiliate_links": [],
        "affiliate_events": [],
    }


def _ensure_dirs() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(VAULT_DIR, exist_ok=True)


def _load_state() -> Dict[str, List[Dict[str, object]]]:
    _ensure_dirs()
    if not STATE_PATH.exists():
        return _default_state()
    try:
        with STATE_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return _default_state()


def _save_state(state: Dict[str, List[Dict[str, object]]]) -> None:
    _ensure_dirs()
    with STATE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)


def _make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _hash_bytes(data: bytes) -> str:
    digest = sha256()
    digest.update(data)
    return digest.hexdigest()


def _write_vault_file(content_bytes: bytes, filename: str) -> Dict[str, str]:
    _ensure_dirs()
    file_hash = _hash_bytes(content_bytes)
    vault_name = f"{file_hash[:16]}_{int(time.time())}_{filename}"
    vault_path = VAULT_DIR / vault_name
    with vault_path.open("wb") as handle:
        handle.write(content_bytes)
    try:
        relative_path = vault_path.relative_to(VAULT_DIR)
    except ValueError:
        relative_path = vault_path.name
    return {"path": str(relative_path), "hash": file_hash}


def create_artist(name: str, payout_acct: Optional[str] = None) -> Artist:
    with LOCK:
        state = _load_state()
        artist = Artist(id=_make_id("artist"), name=name, payout_acct=payout_acct)
        state["artists"].append(artist.to_dict())
        _save_state(state)
    audit_ndjson("fancomp_artist_create", artist_id=artist.id, name=name)
    return artist


def list_artists() -> List[Dict[str, object]]:
    state = _load_state()
    return list(state.get("artists", []))


def get_artist(artist_id: str) -> Optional[Artist]:
    state = _load_state()
    for payload in state.get("artists", []):
        if payload.get("id") == artist_id:
            return Artist(**payload)  # type: ignore[arg-type]
    return None


def ingest_content(
    artist_id: str,
    title: str,
    price_cents: int,
    kind: str,
    license_terms: str,
    metadata: Optional[Dict[str, object]] = None,
    file_bytes: Optional[bytes] = None,
    filename: str = "asset.bin",
    percent_alloc: float = 0.0,
) -> Content:
    metadata = metadata or {}
    with LOCK:
        state = _load_state()
        artist = get_artist(artist_id)
        if artist is None:
            raise ValueError("artist not found")
        vault_info = None
        if file_bytes is not None:
            vault_info = _write_vault_file(file_bytes, filename)
        content = Content(
            id=_make_id("content"),
            artist_id=artist_id,
            title=title,
            price_cents=int(price_cents),
            kind=kind,
            hash=(vault_info or {}).get("hash", ""),
            license_terms=license_terms,
            metadata=dict(metadata),
        )
        if vault_info is not None:
            content.metadata["vault_path"] = vault_info["path"]
        state.setdefault("content", []).append(content.to_dict())
        # Ensure pool exists per content for bookkeeping
        pool = MoneyPool(
            id=_make_id("pool"),
            content_id=content.id,
            percent_alloc=float(percent_alloc),
            enabled=bool(percent_alloc and percent_alloc > 0.0),
        )
        state.setdefault("pools", []).append(pool.to_dict())
        _save_state(state)
    audit_ndjson("fancomp_upload_ip", content_id=content.id, artist_id=artist_id, hash=content.hash)
    return content


def _resolve_pool(state: Dict[str, List[Dict[str, object]]], content_id: str) -> Optional[MoneyPool]:
    for payload in state.get("pools", []):
        if payload.get("content_id") == content_id:
            return MoneyPool(**payload)  # type: ignore[arg-type]
    return None


def record_purchase(content_id: str, buyer_id: str, amount_cents: int, affiliate_code: Optional[str] = None) -> Transaction:
    with LOCK:
        state = _load_state()
        tx = Transaction(
            id=_make_id("tx"),
            content_id=content_id,
            buyer_id=buyer_id,
            amount_cents=int(amount_cents),
        )
        affiliate: Optional[AffiliateLink] = None
        if affiliate_code:
            for payload in state.get("affiliate_links", []):
                if payload.get("code") == affiliate_code:
                    affiliate = AffiliateLink(**payload)  # type: ignore[arg-type]
                    tx.affiliate_id = affiliate.id
                    break
        state.setdefault("transactions", []).append(tx.to_dict())

        pool_payload = _resolve_pool(state, content_id)
        if pool_payload is not None and pool_payload.enabled and pool_payload.percent_alloc > 0:
            pool_payload.balance_cents += int(amount_cents * (pool_payload.percent_alloc / 100.0))
            entry = PoolEntry(
                id=_make_id("entry"),
                pool_id=pool_payload.id,
                user_id=buyer_id,
                tx_id=tx.id,
            )
            state.setdefault("pool_entries", []).append(entry.to_dict())
            # Update pool record
            for idx, payload in enumerate(state.get("pools", [])):
                if payload.get("id") == pool_payload.id:
                    state["pools"][idx] = pool_payload.to_dict()
                    break
        if affiliate is not None:
            event = _track_affiliate_locked(state, affiliate, tx.id)
            state.setdefault("affiliate_events", []).append(event.to_dict())
        _save_state(state)
    audit_ndjson(
        "fancomp_purchase_paper",
        content_id=content_id,
        buyer_id=buyer_id,
        amount_cents=amount_cents,
        affiliate_code=affiliate_code,
        tx_id=tx.id,
    )
    return tx


def _track_affiliate_locked(state: Dict[str, List[Dict[str, object]]], link: AffiliateLink, tx_id: Optional[str]) -> AffiliateEvent:
    event = None
    for payload in state.get("affiliate_events", []):
        if payload.get("link_id") == link.id:
            event = AffiliateEvent(**payload)  # type: ignore[arg-type]
            break
    if event is None:
        event = AffiliateEvent(id=_make_id("affevt"), link_id=link.id, tx_id=tx_id, clicks=0, conversions=0)
    event.clicks += 1
    if tx_id:
        event.conversions += 1
        event.tx_id = tx_id
    event.last_event_at = time.time()
    # Replace existing entry
    new_events: List[Dict[str, object]] = []
    replaced = False
    for payload in state.get("affiliate_events", []):
        if payload.get("id") == event.id:
            new_events.append(event.to_dict())
            replaced = True
        else:
            new_events.append(payload)
    if not replaced:
        new_events.append(event.to_dict())
    state["affiliate_events"] = new_events
    return event


def create_affiliate_link(artist_id: Optional[str], rate_bps: int) -> AffiliateLink:
    with LOCK:
        state = _load_state()
        link = AffiliateLink(id=_make_id("aff"), artist_id=artist_id, code=_make_id("code")[-6:], rate_bps=int(rate_bps))
        state.setdefault("affiliate_links", []).append(link.to_dict())
        _save_state(state)
    audit_ndjson("fancomp_affiliate_create", link_id=link.id, artist_id=artist_id, rate_bps=rate_bps)
    return link


def affiliate_stats(code: str) -> Dict[str, object]:
    state = _load_state()
    link_payload = None
    for payload in state.get("affiliate_links", []):
        if payload.get("code") == code:
            link_payload = payload
            break
    if link_payload is None:
        raise ValueError("affiliate code not found")
    events = [payload for payload in state.get("affiliate_events", []) if payload.get("link_id") == link_payload["id"]]
    conversions = sum(_to_int(evt.get("conversions", 0)) for evt in events)
    clicks = sum(_to_int(evt.get("clicks", 0)) for evt in events)
    return {
        "link": link_payload,
        "clicks": clicks,
        "conversions": conversions,
        "events": events,
    }


def pool_state(content_id: str) -> Dict[str, object]:
    state = _load_state()
    pool_payload = _resolve_pool(state, content_id)
    entries = [payload for payload in state.get("pool_entries", []) if payload.get("pool_id") == (pool_payload.id if pool_payload else "")]
    draws = [payload for payload in state.get("draws", []) if payload.get("pool_id") == (pool_payload.id if pool_payload else "")]
    return {
        "pool": pool_payload.to_dict() if pool_payload else None,
        "entries": entries,
        "draws": draws,
        "rules_link": compliance.official_rules(),
    }


def run_pool_draw(pool_id: str, sample_size: int = 1) -> PoolDraw:
    if not compliance.sweepstakes_enabled():
        raise PermissionError("sweepstakes disabled")
    with LOCK:
        state = _load_state()
        entries = [payload for payload in state.get("pool_entries", []) if payload.get("pool_id") == pool_id]
        if not entries:
            raise ValueError("no entries for pool")
        seed = secrets.token_hex(8)
        random.Random(seed).shuffle(entries)
        winners = entries[: sample_size or 1]
        draw = PoolDraw(
            id=_make_id("draw"),
            pool_id=pool_id,
            ts=time.time(),
            winners_json=winners,
            seed=seed,
            status="paper_pending",
        )
        state.setdefault("draws", []).append(draw.to_dict())
        _save_state(state)
    audit_ndjson("fancomp_pool_draw", pool_id=pool_id, winners=winners, seed=seed)
    return draw


def metrics() -> MetricsPayload:
    state = _load_state()
    artists = state.get("artists", [])
    content_items = state.get("content", [])
    transactions = state.get("transactions", [])
    total_revenue = sum(_to_int(item.get("amount_cents", 0)) for item in transactions)
    pools = state.get("pools", [])
    pool_balances = sum(_to_int(item.get("balance_cents", 0)) for item in pools)
    return MetricsPayload(
        artists=len(artists),
        content=len(content_items),
        transactions=len(transactions),
        revenue_cents=total_revenue,
        pool_balance_cents=pool_balances,
    )


def dashboard() -> Dict[str, object]:
    metrics_payload = metrics()
    state = _load_state()
    recent_content = sorted(
        state.get("content", []),
        key=lambda item: _to_float(item.get("created_at", 0.0)),
        reverse=True,
    )[:5]
    recent_purchases = sorted(
        state.get("transactions", []),
        key=lambda item: _to_float(item.get("created_at", 0.0)),
        reverse=True,
    )[:5]
    return {
        "widgets": {
            "kpis": [
                {"name": "Artists", "value": metrics_payload["artists"]},
                {"name": "Content", "value": metrics_payload["content"]},
                {"name": "Purchases", "value": metrics_payload["transactions"]},
                {
                    "name": "Revenue (paper)",
                    "value": _to_float(metrics_payload["revenue_cents"]) / 100.0,
                    "unit": "SER paper",
                },
                {
                    "name": "Pool Balance",
                    "value": _to_float(metrics_payload["pool_balance_cents"]) / 100.0,
                    "unit": "SER paper",
                },
            ],
            "tables": [
                {
                    "title": "Recent Content",
                    "rows": [
                        {
                            "title": item.get("title"),
                            "artist_id": item.get("artist_id"),
                            "price_cents": item.get("price_cents"),
                            "created_at": item.get("created_at"),
                        }
                        for item in recent_content
                    ],
                },
                {
                    "title": "Recent Purchases",
                    "rows": [
                        {
                            "content_id": item.get("content_id"),
                            "buyer_id": item.get("buyer_id"),
                            "amount_cents": item.get("amount_cents"),
                            "created_at": item.get("created_at"),
                        }
                        for item in recent_purchases
                    ],
                },
            ],
        }
    }
