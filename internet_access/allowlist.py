from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

_DEFAULT_ALLOWLIST: Dict[str, Any] = {
    "domains": [
        {"host": "example.com", "verbs": ["GET"], "rate": {"per_min": 60}},
    ],
    "read_only": True,
}

_ALLOWLIST_PATH = Path(os.environ.get("INTERNET_ALLOWLIST_PATH", "logs/allowlist.json"))


def _clone_default() -> Dict[str, Any]:
    data = json.loads(json.dumps(_DEFAULT_ALLOWLIST))
    return data


def load_allowlist() -> Dict[str, Any]:
    """Return the current internet allowlist, falling back to the default structure."""

    path = _ALLOWLIST_PATH
    if not path.exists():
        return _clone_default()
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return _clone_default()
        domains = data.get("domains") or []
        if not isinstance(domains, list):
            domains = []
        read_only = bool(data.get("read_only", True))
        return {"domains": domains, "read_only": read_only}
    except Exception:
        return _clone_default()


def _normalize_domains(domains: Any) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    if not isinstance(domains, list):
        return normalized
    for item in domains:
        if not isinstance(item, dict):
            continue
        host = str(item.get("host", "")).strip()
        if not host:
            continue
        verbs_raw = item.get("verbs") or ["GET"]
        if isinstance(verbs_raw, list):
            verbs = [str(verb).upper() for verb in verbs_raw if str(verb).strip()]
        else:
            verbs = [str(verbs_raw).upper()]
        verbs = verbs or ["GET"]
        rate_raw = item.get("rate")
        per_min = 60
        if isinstance(rate_raw, dict):
            try:
                per_min = int(rate_raw.get("per_min", per_min))
            except Exception:
                per_min = 60
        normalized.append({"host": host, "verbs": verbs, "rate": {"per_min": max(per_min, 1)}})
    return normalized


def save_allowlist(data: Dict[str, Any]) -> Dict[str, Any]:
    """Persist the allowlist if it is writable; raises PermissionError otherwise."""

    current = load_allowlist()
    if current.get("read_only", True):
        raise PermissionError("Allowlist is read-only; toggle read_only to false to permit updates.")

    normalized = {
        "domains": _normalize_domains(data.get("domains")),
        "read_only": bool(data.get("read_only", False)),
    }

    path = _ALLOWLIST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(normalized, handle, ensure_ascii=False, indent=2)
    return normalized
