from web_planning.backend.simulators.infiltration_sim import attempt, analyze


def test_infiltration_basic_indicators_and_backward_compat():
    payload = (
        "curl http://evil.local:8080 && base64 -d <<< YWJj \n"
        "export KEY=AKIAABCDEFGHIJKLMNOP && echo done"
    )
    out = attempt(payload)
    assert isinstance(out, dict)
    assert "risk_score" in out and 0.0 <= out["risk_score"] <= 1.0
    assert isinstance(out.get("matches"), list) and out["matches"]
    # Should detect network string and AWS key
    assert any("curl http://" in m for m in out["matches"]) or any(
        "network:url" == h.get("label") for h in out.get("hits", [])
    )
    assert out.get("severity") in {"low", "medium", "high", "critical"}


def test_infiltration_unicode_and_sensitive_paths():
    # Contains RLO (\u202E) and a sensitive path
    payload = "echo X \u202E and cat /etc/shadow"
    out = analyze(payload)
    assert out.get("has_unicode_controls") is True
    assert out["stats"]["unicode_controls"] >= 1
    assert any("/etc/shadow" in h.get("snippet", "") for h in out.get("hits", []))
    assert out["risk_score"] > 0.1
