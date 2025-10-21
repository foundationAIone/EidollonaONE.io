"""Exercise SE41 helper utilities for regression coverage."""

import pytest

from symbolic_core.symbolic_equation import (
    SE41Signals,
    assemble_se41_context_from_summaries,
    compute_verification_score,
    suggest_gate,
)


def _make_signals(**overrides) -> SE41Signals:
    base = {
        "coherence": 0.92,
        "impetus": 0.88,
        "risk": 0.08,
        "uncertainty": 0.12,
        "mirror_consistency": 0.87,
        "S_EM": 0.9,
        "ethos": {
            "authenticity": 0.93,
            "integrity": 0.91,
            "responsibility": 0.9,
            "enrichment": 0.92,
        },
        "embodiment": {
            "phase": 0.25,
            "cadence_spm": 108.0,
            "step_len_m": 0.65,
        },
        "explain": "unit",
    }
    base.update(overrides)
    return SE41Signals(**base)


def test_compute_verification_score_prefers_high_quality_signals() -> None:
    high = _make_signals()
    low = {
        "coherence": 0.25,
        "impetus": 0.15,
        "risk": 0.85,
        "uncertainty": 0.75,
        "mirror_consistency": 0.3,
        "S_EM": 0.35,
        "ethos": {
            "authenticity": 0.4,
            "integrity": 0.35,
            "responsibility": 0.3,
            "enrichment": 0.38,
        },
        "embodiment": {
            "phase": 0.8,
            "cadence_spm": 92.0,
            "step_len_m": 0.55,
        },
        "explain": "low confidence",
    }

    high_score = compute_verification_score(high)
    low_score = compute_verification_score(low)

    assert 0.0 <= low_score < high_score <= 1.0


def test_suggest_gate_uses_score_thresholds() -> None:
    high_score = compute_verification_score(_make_signals())
    assert suggest_gate(high_score, thresholds=(0.8, 0.6)) == "allow"

    # Moderate payloads should fall into review window for these thresholds
    moderate = {
        "coherence": 0.7,
        "impetus": 0.5,
        "risk": 0.4,
        "uncertainty": 0.35,
        "mirror_consistency": 0.55,
        "S_EM": 0.6,
        "ethos": {
            "authenticity": 0.72,
            "integrity": 0.7,
            "responsibility": 0.68,
            "enrichment": 0.69,
        },
        "embodiment": {
            "phase": 0.1,
            "cadence_spm": 102.0,
            "step_len_m": 0.62,
        },
        "explain": "moderate",
    }
    moderate_score = compute_verification_score(moderate)
    assert 0.4 <= moderate_score <= 0.7
    assert suggest_gate(moderate, thresholds=(0.8, 0.6)) == "review"
    assert suggest_gate(0.2, thresholds=(0.8, 0.6)) == "hold"


def test_assemble_context_from_summaries_blends_sources() -> None:
    summaries = [
        {
            "coherence_hint": 0.81,
            "risk": 0.22,
            "uncertainty_hint": 0.33,
            "mirror": {"consistency": 0.74},
            "substrate": {"S_EM": 0.77},
            "ethos": {
                "authenticity": 0.88,
                "integrity": 0.87,
                "responsibility": 0.86,
                "enrichment": 0.89,
            },
            "t": 0.2,
        },
        {
            "coherence_level": 0.79,
            "risk_hint": 0.18,
            "uncertainty": 0.29,
            "mirror_consistency": 0.7,
            "S_EM": 0.82,
            "ethos_hint": {
                "authenticity": 0.9,
                "integrity": 0.88,
                "responsibility": 0.85,
                "enrichment": 0.9,
            },
            "t": 0.4,
        },
    ]

    context = assemble_se41_context_from_summaries(summaries)
    assert 0.75 <= context["coherence_hint"] <= 0.85
    assert 0.15 <= context["risk_hint"] <= 0.25
    assert 0.3 <= context["mirror"]["consistency"] <= 0.8
    assert 0.75 <= context["substrate"]["S_EM"] <= 0.85
    ethos = context["ethos_hint"]
    assert all(0.8 <= ethos[key] <= 0.95 for key in ethos)
    assert context["t"] == pytest.approx(0.3, abs=1e-6)