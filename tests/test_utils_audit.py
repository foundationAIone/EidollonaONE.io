from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

from utils.audit import audit_ndjson, register_sink


def test_audit_ndjson_writes_file(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    os.environ["AUDIT_LOG_DIR"] = str(logs_dir)
    try:
        audit_ndjson("test_event", foo="bar")
        path = logs_dir / "audit.ndjson"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["event"] == "test_event"
        assert data["foo"] == "bar"
        assert "ts" in data
    finally:
        os.environ.pop("AUDIT_LOG_DIR", None)


def test_register_sink_receives_payload(tmp_path: Path) -> None:
    received: Dict[str, Dict] = {}

    def sink(payload: Dict[str, object]) -> None:
        received["payload"] = payload

    register_sink(sink)
    try:
        audit_ndjson("another_event", value=42)
    finally:
        register_sink(None)

    assert "payload" in received
    payload = received["payload"]
    assert payload["event"] == "another_event"
    assert payload["value"] == 42
    assert "ts" in payload
