# -*- coding: utf-8 -*-
from fastapi.testclient import TestClient
from web_planning.backend.main import app, ADMIN_USER, ADMIN_PASS


def _auth_headers():
    return {
        "Authorization": "Basic "
        + ((ADMIN_USER + ":" + ADMIN_PASS).encode("utf-8")).decode("utf-8")
    }


def test_governance_policy_endpoint():
    client = TestClient(app)
    res = client.get("/governance/policy", auth=(ADMIN_USER, ADMIN_PASS))
    assert res.status_code == 200, res.text
    data = res.json()
    assert "policy" in data
    assert data["policy"].get("default") == "deny"


def test_governance_authorize_deny_by_default():
    client = TestClient(app)
    payload = {"action": "plan.create", "actor": "someone"}
    res = client.post(
        "/governance/authorize", json=payload, auth=(ADMIN_USER, ADMIN_PASS)
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["allowed"] is False
    assert data["reason"].startswith("default:"), data
