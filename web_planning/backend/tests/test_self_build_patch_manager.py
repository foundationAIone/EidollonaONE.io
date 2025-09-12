from web_planning.backend.self_build.codegen import propose_patch
from web_planning.backend.self_build.patch_manager import (
    validate_diff,
    ingest_patch,
    list_patches,
    delete_patch,
)


def test_validate_and_ingest_add_only_patch(tmp_path, monkeypatch):
    # Isolate patch dir
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    # Generate safe diff from codegen
    diff = propose_patch({"id": "T-abc", "title": "Demo"})
    details = validate_diff(diff)
    assert details["ok"] is True
    r = ingest_patch("demo", diff)
    assert r["ok"] is True
    items = list_patches()
    assert any(it.get("id") == "demo" for it in items)
    assert delete_patch("demo") is True


def test_reject_unsafe_diff():
    # Delete/rename should be rejected
    diff = """diff --git a/foo.txt b/bar.txt\nrename from foo.txt\nrename to bar.txt\n--- a/foo.txt\n+++ b/bar.txt\n@@\n+hello\n"""
    details = validate_diff(diff)
    assert details["ok"] is False
