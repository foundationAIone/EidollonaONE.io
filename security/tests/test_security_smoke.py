from __future__ import annotations

from security.auth import check_token
from security.policy import get_policy


def test_policy_has_token():
    policy = get_policy()
    allowed = policy.get("tokens", {}).get("allowed", [])
    assert "dev-token" in allowed


def test_check_token():
    ok, _ = check_token("dev-token")
    assert ok is True
    bad, _ = check_token("invalid")
    assert bad is False
