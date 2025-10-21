from fastapi.testclient import TestClient

try:
    from bridge.alpha_tap import app
except Exception:  # pragma: no cover - import guard for constrained envs
    app = None

TOKEN = "dev-token"


def get_client() -> TestClient:
    assert app is not None, "AlphaTap FastAPI app unavailable"
    return TestClient(app)


def test_charter_endpoint_returns_pillars():
    client = get_client()
    response = client.get("/v1/sovereign/charter", params={"token": TOKEN})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("ok") is True
    charter = data.get("charter") or {}
    assert charter.get("entity") == "Eidollona"
    pillars = charter.get("four_pillars") or []
    assert set(pillars) == {"authenticity", "integrity", "responsibility", "enrichment"}


def test_resonance_tones_endpoint():
    client = get_client()
    payload = {"coherence": 0.8, "risk": 0.15}
    response = client.post("/v1/resonance/tones", params={"token": TOKEN}, json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("ok") is True
    resonance = data.get("resonance") or {}
    tones = resonance.get("tones") or []
    assert len(tones) == 12
    assert all(isinstance(freq, (int, float)) for freq in tones)
    assert resonance.get("cadence_ms") in {600, 900}


def test_stewardship_ouroboros_endpoint():
    client = get_client()
    metrics = {"waste": 0.5, "oscillation": 0.4, "stasis": 0.2, "novelty": 0.6}
    response = client.post("/v1/stewardship/ouroboros", params={"token": TOKEN}, json=metrics)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("ok") is True
    diagnosis = data.get("diagnosis") or {}
    assert 0.0 <= diagnosis.get("score", 0.0) <= 1.0


def test_nodes_dialogue_round_trip():
    client = get_client()
    node_id = "node-07"
    open_response = client.post("/v1/nodes/open", params={"token": TOKEN, "node_id": node_id})
    assert open_response.status_code == 200, open_response.text
    opened = open_response.json()
    assert opened.get("ok") is True
    assert opened.get("node") == node_id

    speak_response = client.post(
        "/v1/nodes/speak",
        params={"token": TOKEN, "node_id": node_id, "msg": "Sovereign pulse"},
    )
    assert speak_response.status_code == 200, speak_response.text
    spoken = speak_response.json()
    assert spoken.get("ok") is True
    assert spoken.get("node") == node_id
    assert "Sovereign pulse" in (spoken.get("reply") or "")
