from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import pytest

BASE = os.getenv("SERPLUS_BASE", "http://127.0.0.1:8802")
TOKEN = os.getenv("SERPLUS_TOKEN", "dev-token")
TIMEOUT = 5


def _build_url(route: str) -> str:
    if "?" in route:
        sep = "&"
    else:
        sep = "?"
    return f"{BASE}{route}{sep}{urlencode({'token': TOKEN})}"


def _get_ser_state():
    url = _build_url("/v1/ser/state")
    try:
        with urlopen(url, timeout=TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8")
    except HTTPError as err:
        if err.code == 404:
            pytest.skip("serplus state endpoint unavailable (404)")
        raise
    except URLError as exc:
        pytest.skip(f"serplus endpoint offline: {exc.reason}")


def test_serplus_state_contains_ledger():
    status, payload = _get_ser_state()
    assert status == 200
    data = json.loads(payload)
    assert isinstance(data, dict)
    assert "state" in data
    assert "ledger" in data
