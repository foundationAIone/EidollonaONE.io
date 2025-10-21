from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - fallback
    def audit(event: str, **payload: Any) -> None:
        return None

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

from trading_engine.options.surface_svi import fit_svi_arbitrage_free, store_params

API_URL = os.getenv("OPTION_SURFACE_SOURCE", "http://127.0.0.1:8802/v1/options/quotes")
TOKEN = os.getenv("ALPHATAP_TOKEN", "dev-token")


def fetch_quotes() -> List[Dict[str, Any]]:
    if httpx is None:
        return []
    try:
        response = httpx.get(API_URL, params={"token": TOKEN}, timeout=5.0)
        if response.status_code >= 400:
            return []
        data = response.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            payload = data.get("quotes")
            if isinstance(payload, list):
                return payload
    except Exception:
        return []
    return []


def main() -> int:
    quotes = fetch_quotes()
    params = fit_svi_arbitrage_free(quotes)
    out_path = store_params(params)
    payload = {
        "ts": datetime.utcnow().isoformat(),
        "path": str(out_path),
        "count": len(quotes),
        "params": params.__dict__,
    }
    audit("svi_nightly", **payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
