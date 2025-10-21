from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

CRITICAL_FILES = [
    "web_interface/static/webview/throne_room.html",
    "web_interface/static/webview/capstone.html",
    "web_interface/static/webview/js/vrm_loader.js",
]


@pytest.mark.parametrize("relative", CRITICAL_FILES)
def test_web_asset_exists(relative: str) -> None:
    target = ROOT / relative
    assert target.exists(), f"missing asset: {relative}"
    assert target.is_file(), f"asset is not a file: {relative}"
    assert target.stat().st_size > 0, f"asset empty: {relative}"
