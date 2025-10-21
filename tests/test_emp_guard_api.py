from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from emp_guard.api.routes import router
from emp_guard.policy import get_posture, reset_posture

app = FastAPI()
app.include_router(router, prefix="/v1/emp-guard")
client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_posture():
    reset_posture()
    yield
    reset_posture()


def test_posture_updates_dashboard(monkeypatch):
    calls = {}

    def fake_update(posture, note=""):
        calls["posture"] = {
            "note": note,
            "exposure": posture.get("exposure"),
        }
        return True

    monkeypatch.setattr("emp_guard.api.routes.update_dashboard", fake_update)
    resp = client.get("/v1/emp-guard/posture", params={"token": "dev-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "posture" in body
    assert calls["posture"]["note"] == "posture viewed"


def test_rebind_skip_updates_dashboard(monkeypatch):
    notes: list[str] = []

    def fake_update(posture, note=""):
        notes.append(note)
        return True

    monkeypatch.setattr("emp_guard.api.routes.update_dashboard", fake_update)
    resp = client.post(
        "/v1/emp-guard/rebind/ethos",
        params={"token": "dev-token"},
        json={"targets": []},
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["rebuilt"] == []
    assert notes and notes[-1] == "rebind skipped"


def test_caps_update_changes_posture(monkeypatch):
    captures: list[tuple[dict, str]] = []

    def fake_update(posture, note=""):
        captures.append((posture["caps"], note))
        return True

    monkeypatch.setattr("emp_guard.api.routes.update_dashboard", fake_update)
    resp = client.post(
        "/v1/emp-guard/posture/caps",
        params={"token": "dev-token"},
        json={"cost_usd_max": 1500.0, "energy_kwh_max": 450.0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["caps"]["cost_usd_max"] == 1500.0
    assert body["caps"]["energy_kwh_max"] == 450.0
    assert captures[-1][1] == "caps updated"
    assert captures[-1][0]["cost_usd_max"] == 1500.0
    assert get_posture()["caps"]["cost_usd_max"] == 1500.0


def test_caps_inspect_when_empty_payload(monkeypatch):
    notes: list[str] = []

    def fake_update(posture, note=""):
        notes.append(note)
        return True

    monkeypatch.setattr("emp_guard.api.routes.update_dashboard", fake_update)
    resp = client.post(
        "/v1/emp-guard/posture/caps", params={"token": "dev-token"}, json={}
    )
    assert resp.status_code == 200
    assert resp.json()["caps"]["cost_usd_max"] == get_posture()["caps"]["cost_usd_max"]
    assert notes and notes[-1] == "caps inspected"


def test_token_required():
    resp = client.get("/v1/emp-guard/posture", params={"token": ""})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "token required"
