from __future__ import annotations

import pytest

from avatar import reactive_layer


@pytest.fixture(autouse=True)
def reset_cache():
    reactive_layer._LAST_CACHE["directive"] = None  # type: ignore[attr-defined]
    reactive_layer._LAST_CACHE["ts"] = 0.0  # type: ignore[attr-defined]
    reactive_layer._LAST_CACHE["signals_hash"] = None  # type: ignore[attr-defined]


def test_generate_directive_deterministic():
    signals = {
        "coherence": 0.82,
        "impetus": 0.58,
        "risk": 0.18,
        "uncertainty": 0.33,
        "mirror_consistency": 0.76,
        "S_EM": 0.81,
        "ethos": {"authenticity": 0.9, "integrity": 0.88},
    }
    directive = reactive_layer.generate_directive(signals=signals, seed=123)
    data = directive.as_dict()
    assert data["mood"] in {"focused", "composed", "alert", "reflective"}
    assert data["field"]["nx"] == 32
    assert data["strategies"]

    summary = reactive_layer.directive_summary(directive)
    assert summary["moves"]["pose"].startswith("focus_") or summary["moves"]["pose"].startswith("grace_")
    assert summary["stats"]["strategy_count"] >= 1

    # Cache reuse within window
    start = directive.updated_at
    cached = reactive_layer.generate_directive(signals=signals, seed=123)
    assert cached is directive or cached.updated_at == start


def test_generate_directive_with_features():
    signals = {
        "coherence": 0.65,
        "impetus": 0.44,
        "risk": 0.35,
        "uncertainty": 0.40,
        "mirror_consistency": 0.68,
        "S_EM": 0.70,
        "ethos": {},
    }
    features = {"sharpness": 0.8}
    directive = reactive_layer.generate_directive(signals=signals, features=features, seed=7)
    assert "animation" in directive.as_dict()
    summary = reactive_layer.directive_summary(directive)
    assert "moves" in summary
