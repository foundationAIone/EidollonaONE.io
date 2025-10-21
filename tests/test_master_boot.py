from __future__ import annotations

from types import SimpleNamespace
from typing import Dict, Any

import pytest

from master_key import master_boot
from symbolic_core.symbolic_equation_master import MasterStateSnapshot


def _snapshot(**overrides: Any) -> MasterStateSnapshot:
    base: Dict[str, Any] = {
        "coherence": 0.82,
        "impetus": 0.70,
        "risk": 0.20,
        "uncertainty": 0.25,
        "mirror_consistency": 0.72,
        "substrate_readiness": 0.80,
        "ethos_min": 0.65,
        "embodiment_phase": 0.10,
        "delta_coherence": 0.01,
        "delta_impetus": 0.01,
        "delta_risk": -0.01,
        "timestamp": 1700000000.0,
        "explain": "ok",
    }
    base.update(overrides)
    return MasterStateSnapshot(**base)


def test_boot_system_allows_when_within_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    events = []
    monkeypatch.setattr(master_boot, "evaluate_master_state", lambda context=None: _snapshot())
    monkeypatch.setattr(
        master_boot,
        "get_master_key",
        lambda: SimpleNamespace(fingerprint="ABCDEF0123456789"),
    )
    monkeypatch.setattr(master_boot, "_gate_logger", lambda: SimpleNamespace(write=events.append))

    report = master_boot.boot_system(policy=master_boot.BootPolicy())

    assert report.ok is True
    assert report.advisories == []
    assert report.summary()["fingerprint"] == "ABCDEF012345"
    assert events, "audit logger should capture an entry"
    assert events[0]["decision"] == "ALLOW"
    assert events[0]["snapshot"]["coherence"] == pytest.approx(0.82)
    assert report.to_dict()["summary"]["ok"] is True


def test_boot_system_produces_advisories_on_policy_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    events = []
    monkeypatch.setattr(
        master_boot,
        "evaluate_master_state",
        lambda context=None: _snapshot(coherence=0.40, substrate_readiness=0.45, risk=0.75, uncertainty=0.90),
    )
    monkeypatch.setattr(master_boot, "get_master_key", lambda: SimpleNamespace(fingerprint="MK"))
    monkeypatch.setattr(master_boot, "_gate_logger", lambda: SimpleNamespace(write=events.append))

    policy = master_boot.BootPolicy(warn_only=True)
    report = master_boot.boot_system(policy=policy)

    assert report.ok is False
    assert "low_coherence" in ";".join(report.advisories)
    assert "high_risk" in ";".join(report.advisories)
    assert events[0]["decision"] == "HOLD"
    assert events[0]["reason"].startswith("low_coherence")
    assert report.details["policy"]["warn_only"] is True


def test_boot_policy_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOOT_MIN_COHERENCE", "0.7")
    monkeypatch.setenv("BOOT_MIN_SUBSTRATE", "0.8")
    monkeypatch.setenv("BOOT_MAX_RISK", "0.5")
    monkeypatch.setenv("BOOT_MAX_UNCERTAINTY", "0.6")
    monkeypatch.setenv("BOOT_WARN_ONLY", "0")

    policy = master_boot.BootPolicy.from_env()

    assert policy.min_coherence == pytest.approx(0.7)
    assert policy.min_substrate == pytest.approx(0.8)
    assert policy.max_risk == pytest.approx(0.5)
    assert policy.max_uncertainty == pytest.approx(0.6)
    assert policy.warn_only is False
