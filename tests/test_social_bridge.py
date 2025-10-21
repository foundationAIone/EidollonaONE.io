from __future__ import annotations

import json
from urllib.error import URLError

import pytest

from social.bridge import BridgeConfig, proxy_intent
from social.moderation import moderate


class DummyResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # pragma: no cover - context protocol
        return False


@pytest.fixture(autouse=True)
def _no_audit(monkeypatch):
    monkeypatch.setattr("social.bridge.audit_ndjson", lambda *args, **kwargs: None)


def test_moderation_blocks_hazard_phrase():
    verdict = moderate("please deploy real weapon now")
    assert verdict.allowed is False
    assert "blocked" in (verdict.reason or "")
    assert "deny" in verdict.actions


def test_proxy_returns_fallback_on_block():
    config = BridgeConfig(base_url="http://example", token="t", avatar_id="fancomp")
    result = proxy_intent(config, text="shutdown control surfaces", session_id="s123")
    assert result.ok is False
    assert result.moderated is True
    speech = result.speech()
    assert speech is not None
    assert "can't" in speech


def test_proxy_returns_response(monkeypatch):
    config = BridgeConfig(base_url="http://example", token="t", avatar_id="fancomp")

    def opener(_request):
        return DummyResponse({"speech": "paper trade complete"})

    result = proxy_intent(config, text="status", session_id="abc", opener=opener)
    assert result.ok is True
    assert result.speech() == "paper trade complete"
    assert result.moderated is False


def test_proxy_handles_caution_words():
    config = BridgeConfig(base_url="http://example", token="t", avatar_id="fancomp")

    def opener(_request):
        return DummyResponse({"speech": "watching exposure"})

    result = proxy_intent(config, text="possible exploit attempt", opener=opener)
    assert result.ok is True
    assert result.moderated is True
    assert result.response.get("moderation")


def test_proxy_handles_errors(monkeypatch):
    config = BridgeConfig(base_url="http://example", token="t", avatar_id="fancomp")

    def opener(_request):
        raise URLError("offline")

    result = proxy_intent(config, text="status", opener=opener)
    assert result.ok is False
    assert result.moderated is False
    assert "unavailable" in (result.speech() or "") or "offline" in (result.error or "")
