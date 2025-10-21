from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from serplus.paths import NFT_PATH
from utils.audit import audit_ndjson


def _ensure_parent() -> None:
    os.makedirs(os.path.dirname(NFT_PATH) or ".", exist_ok=True)


def _load() -> Dict[str, Any]:
    _ensure_parent()
    if not os.path.exists(NFT_PATH):
        return {"tokens": []}
    try:
        with open(NFT_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:  # pragma: no cover - fallback if file corrupted
        return {"tokens": []}


def _save(payload: Dict[str, Any]) -> None:
    _ensure_parent()
    with open(NFT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def register_token(token_id: str, owner: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not token_id:
        raise ValueError("token_id is required")
    if not owner:
        raise ValueError("owner is required")
    db = _load()
    tokens: List[Dict[str, Any]] = db.setdefault("tokens", [])
    existing = next((t for t in tokens if t.get("id") == token_id), None)
    if existing:
        existing["owner"] = owner
        if meta:
            current = dict(existing.get("meta") or {})
            current.update(meta)
            existing["meta"] = current
        record = existing
    else:
        record = {"id": token_id, "owner": owner, "meta": meta or {}}
        tokens.append(record)
    _save(db)
    audit_ndjson("serplus_nft_register", token_id=token_id, owner=owner, meta=meta or {})
    return record


def tokens_by_owner(owner: str) -> List[Dict[str, Any]]:
    if not owner:
        return []
    db = _load()
    return [t for t in db.get("tokens", []) if t.get("owner") == owner]


def all_tokens() -> List[Dict[str, Any]]:
    db = _load()
    return list(db.get("tokens", []))


def reset_registry() -> None:
    _save({"tokens": []})


__all__ = ["register_token", "tokens_by_owner", "all_tokens", "reset_registry"]
