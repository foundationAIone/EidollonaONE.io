from __future__ import annotations

import importlib
import json
import sys

import pytest


@pytest.fixture()
def pref_module(tmp_path, monkeypatch):
    prefs_path = tmp_path / "prefs.json"
    monkeypatch.setenv("SOVEREIGN_PREFS_PATH", str(prefs_path))
    if "sovereignty.preferences" in sys.modules:
        sys.modules.pop("sovereignty.preferences")
    module = importlib.import_module("sovereignty.preferences")
    yield module
    if prefs_path.exists():
        raw = json.loads(prefs_path.read_text(encoding="utf-8"))
        assert isinstance(raw, dict)


def test_preferences_roundtrip(pref_module):
    prefs = pref_module.get_preferences()
    assert pytest.approx(prefs["coherence_min"], rel=1e-6) == 0.78

    updated = pref_module.update_preferences({"coherence_min": 0.84, "notes": "QA"}, actor="dev-token")
    assert pytest.approx(updated["coherence_min"], rel=1e-6) == 0.84
    assert updated["notes"] == "QA"
    assert updated["updated_by"] == "dev-token"

    reset = pref_module.reset_preferences(actor="ops")
    assert pytest.approx(reset["coherence_min"], rel=1e-6) == 0.78
    assert reset["updated_by"] == "ops"


def test_preferences_reject_invalid(pref_module):
    with pytest.raises(ValueError):
        pref_module.update_preferences({}, actor="ops")
    prefs = pref_module.get_preferences()
    assert "coherence_min" in prefs
