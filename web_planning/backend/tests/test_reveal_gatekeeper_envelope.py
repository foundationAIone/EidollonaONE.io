import time

from web_planning.backend.reveal.gatekeeper import Gatekeeper
from web_planning.backend.reveal.key_envelope import (
    create_envelope,
    resolve_envelope,
    status,
)


def test_gatekeeper_quorum_basic():
    g = Gatekeeper(quorum=2, allow_veto=True)
    assert g.status()["remaining_for_quorum"] == 2
    g.submit("alice", True)
    assert g.status()["remaining_for_quorum"] == 1
    g.submit("bob", False)  # veto
    assert g.is_open() is False
    g.submit("bob", True)  # change of mind
    assert g.is_open() is True


def test_gatekeeper_expiry():
    g = Gatekeeper(quorum=1, expiry_seconds=1)
    g.submit("alice", True)
    assert g.is_open() is True
    time.sleep(1.2)
    assert g.is_open() is False


def test_envelope_resolve_flow(tmp_path, monkeypatch):
    # Use a temp dir for envelope storage
    monkeypatch.setenv("REVEAL_STATE_DIR", str(tmp_path))
    g = Gatekeeper(quorum=1)

    env = create_envelope(
        "ok-consent", ttl_seconds=5, artifact_ref="run-1", meta={"k": 1}
    )
    st = status(env.envelope_id)
    assert st["ok"] is True and st["state"]["opened"] is False

    # Wrong consent
    r = resolve_envelope(env.envelope_id, consent_key="bad", gatekeeper=g)
    assert r["ok"] is False and r["error"] == "invalid_consent"

    # Not yet open without quorum
    g2 = Gatekeeper(quorum=2)
    r = resolve_envelope(
        env.envelope_id,
        consent_key="ok-consent",
        gatekeeper=g2,
        require_open_quorum=True,
    )
    assert r["ok"] is False and r["error"] == "quorum_not_open"

    # Provide approval and open
    g.submit("alice", True)
    r = resolve_envelope(
        env.envelope_id,
        consent_key="ok-consent",
        gatekeeper=g,
        require_open_quorum=True,
    )
    assert r["ok"] is True
    st2 = status(env.envelope_id)
    assert st2["ok"] is True and st2["state"]["opened"] is True
