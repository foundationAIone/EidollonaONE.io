from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import pytest

BASE = os.getenv("BRIDGE_BASE", "http://127.0.0.1:8802")
TOKEN = os.getenv("BRIDGE_TOKEN", "dev-token")
TIMEOUT = 5


def _build_url(route: str) -> str:
    if "?" in route:
        sep = "&"
    else:
        sep = "?"
    return f"{BASE}{route}{sep}{urlencode({'token': TOKEN})}"


def _get(route: str):
    url = _build_url(route)
    try:
        with urlopen(url, timeout=TIMEOUT) as resp:
            payload = resp.read().decode("utf-8")
            return resp.status, payload
    except URLError as exc:
        pytest.skip(f"bridge unavailable: {exc.reason}")


def test_healthz_ping():
    status, _ = _get("/healthz")
    assert status == 200


def test_status_summary_shape():
    status, payload = _get("/v1/status/summary")
    assert status == 200
    data = json.loads(payload)
    assert "gate" in data
    assert "signals" in data
