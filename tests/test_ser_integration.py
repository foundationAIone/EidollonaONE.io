import json
from fastapi.testclient import TestClient


def test_mirror_reflect_appends_jsonl(tmp_path, monkeypatch):
    # Redirect SER path to a temp file for the test to avoid touching real logs
    ser_path = tmp_path / "ser.log.jsonl"
    monkeypatch.setenv("EIDOLLONA_SER_PATH", str(ser_path))

    # Import app after setting env var so the writer uses our path
    app = None
    try:
        from web_planning.backend.main import create_app as planning_create_app

        app = planning_create_app()
    except Exception:
        try:
            from web_interface.server.main import app as web_app

            app = web_app
        except Exception:
            # Fallback: import prebuilt app, relying on startup hook
            from web_planning.backend.main import app as planning_app

            app = planning_app

    # Ensure path clean
    if ser_path.exists():
        ser_path.unlink()

    client = TestClient(app)

    # Predict then reflect
    r = client.post(
        "/mirror/predict",
        json={
            "self_id": "EidollonaONE",
            "route": "/avatar",
            "avatar_loaded": True,
            "env": "WEB",
        },
    )
    assert r.status_code == 200
    r = client.post(
        "/mirror/reflect",
        json={
            "self_id": "EidollonaONE",
            "route": "/avatar",
            "avatar_loaded": True,
            "sensors_ok": True,
            "env": "WEB",
        },
    )
    assert r.status_code == 200

    # Ensure a JSONL line exists with expected fields
    assert ser_path.exists()
    lines = ser_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 1
    last = json.loads(lines[-1])
    assert "ts" in last and "env" in last and last.get("env") in ("WEB", "AR", "VR")
    assert "prediction" in last and "observation" in last
    assert "ser" in last and isinstance(last["ser"], dict)
    assert "score" in last["ser"] and 0.0 <= float(last["ser"]["score"]) <= 1.0
