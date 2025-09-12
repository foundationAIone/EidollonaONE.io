from web_planning.backend.reveal.orchestrator import RevealOrchestrator


def test_preview_includes_emoji_and_fingerprint():
    r = RevealOrchestrator(quorum=2)
    out = r.preview("TEST_INTENT", meta={"x": 1})
    assert out["safe"] is True
    assert isinstance(out.get("emoji_packet"), str) and len(out["emoji_packet"]) > 0
    assert isinstance(out.get("emoji_legacy"), str) and len(out["emoji_legacy"]) > 0
    assert out.get("valid") is True
    assert isinstance(out.get("fingerprint"), str)


def test_quorum_through_orchestrator_and_envelopes(tmp_path, monkeypatch):
    monkeypatch.setenv("REVEAL_STATE_DIR", str(tmp_path))
    r = RevealOrchestrator(quorum=2)

    # Gate initially closed
    assert r.gate_status()["open"] is False

    # Create envelope
    env = r.create_envelope("consent", ttl_seconds=5, artifact_ref="ref-1")
    env_id = env["envelope"]["envelope_id"]

    # Try resolve without quorum -> blocked
    res = r.resolve_envelope(env_id, consent_key="consent", require_open_quorum=True)
    assert res["ok"] is False and res["error"] == "quorum_not_open"

    # Approvals
    r.submit_approval("alice", True)
    r.submit_approval("bob", True)
    assert r.gate_status()["open"] is True

    # Now resolve OK
    res = r.resolve_envelope(env_id, consent_key="consent", require_open_quorum=True)
    assert res["ok"] is True

    # Already opened
    res2 = r.resolve_envelope(env_id, consent_key="consent", require_open_quorum=True)
    assert res2["ok"] is False and res2["error"] == "already_opened"
