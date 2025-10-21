from __future__ import annotations

import json
import os
from typing import Any, Dict

from serplus.paths import ACCOUNTS_PATH


def _load() -> Dict[str, Any]:
    os.makedirs(os.path.dirname(ACCOUNTS_PATH), exist_ok=True)
    if not os.path.exists(ACCOUNTS_PATH):
        return {"accounts": {}}
    try:
        with open(ACCOUNTS_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {"accounts": {}}


def _save(db: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(ACCOUNTS_PATH), exist_ok=True)
    with open(ACCOUNTS_PATH, "w", encoding="utf-8") as handle:
        json.dump(db, handle, ensure_ascii=False, indent=2)


def ensure_account(acct: str, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    db = _load()
    accounts = db.setdefault("accounts", {})
    account = accounts.get(acct)
    if not account:
        account = {
            "id": acct,
            "meta": meta or {"label": acct},
        }
        accounts[acct] = account
        _save(db)
        return account

    if meta:
        current = dict(account.get("meta") or {})
        current.update(meta)
        account["meta"] = current
        accounts[acct] = account
        _save(db)
    return account


def all_accounts() -> Dict[str, Any]:
    return _load().get("accounts", {})
