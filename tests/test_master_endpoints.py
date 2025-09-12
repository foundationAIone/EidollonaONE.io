from fastapi.testclient import TestClient

try:
    from web_planning.backend.main import app
except Exception:  # fallback if backend not present in some environments
    app = None


def test_master_status_endpoint():
    assert app is not None, "FastAPI app not importable"
    c = TestClient(app)
    r = c.get("/master/status")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ok") is True
    # fingerprint + snapshot
    assert "fingerprint" in data
    snap = data.get("snapshot") or {}
    # current backend exposes these condensed fields
    for k in [
        "coherence",
        "impetus",
        "risk",
        "uncertainty",
        "mirror_consistency",
        "substrate_readiness",
        "ethos_min",
        "embodiment_phase",
    ]:
        assert k in snap, f"missing field {k}"
    assert 0.0 <= snap["coherence"] <= 1.0


def test_master_awaken_endpoint():
    assert app is not None
    c = TestClient(app)
    r = c.get("/master/awaken")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    awakening = data.get("awakening") or {}
    # readiness is a string classification directly
    readiness = awakening.get("readiness")
    assert readiness in {"prime_ready", "ready", "warming", "baseline"}
    # basic numeric fields exist
    for k in [
        "coherence",
        "impetus",
        "risk",
        "uncertainty",
        "substrate",
        "mirror",
        "ethos_min",
    ]:
        assert k in awakening
