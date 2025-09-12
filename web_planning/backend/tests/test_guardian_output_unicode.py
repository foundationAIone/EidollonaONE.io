import base64


from web_planning.backend.guardian.output_encoder import safe_preview
from web_planning.backend.guardian.unicode_sanitizer import sanitize_and_score


def test_safe_preview_benign(monkeypatch):
    # Ensure hard-block mode (soft mode off)
    monkeypatch.delenv("GUARDIAN_OUTPUT_SOFT_MODE", raising=False)
    payload = {"id": "x1", "content": "hello world"}
    out = safe_preview(payload)
    assert out.get("preview_only") is True
    assert out.get("redacted") is False
    assert out.get("truncated") is False
    assert out.get("length_bytes") == len("hello world".encode("utf-8"))
    # content_b64 exists and decodes to original
    b64 = out.get("content_b64")
    assert isinstance(b64, str) and len(b64) > 0
    assert base64.b64decode(b64.encode("ascii")).decode("utf-8") == "hello world"


def test_safe_preview_secret_blocked(monkeypatch):
    # Hard-block mode
    monkeypatch.delenv("GUARDIAN_OUTPUT_SOFT_MODE", raising=False)
    secret = "AKIA" + ("A" * 16)
    payload = {"id": "x2", "content": f"key={secret}"}
    out = safe_preview(payload)
    # On block, shape contains no content_b64, but includes reason and dlp metadata
    assert out.get("preview_only") is True
    assert out.get("blocked") is True
    assert "content_b64" not in out
    assert out.get("reason") in {"secret-detected", None}
    assert isinstance(out.get("length_bytes"), int) and out["length_bytes"] > 0


def test_unicode_sanitize_invisible_removed():
    text = "A\u200bB"  # includes ZERO WIDTH SPACE
    norm, info = sanitize_and_score(text)
    assert norm == "AB"
    assert info["removed_invisible"] >= 1
    # Risk scoring presence (no specific threshold assumption)
    assert 0.0 <= info["risk"] <= 1.0
