from web_planning.backend.simulators.redteam_lab import (
    generate_samples,
    evaluate_samples,
    prompt_injection_samples,
)


def test_generate_samples_and_evaluate():
    samples = generate_samples(count=5, unicode_controls=True, seed=42)
    assert len(samples) == 5
    assert all("text" in s and "category" in s for s in samples)

    summary = evaluate_samples(samples)
    assert summary["total"] == 5
    assert "severity_counts" in summary and isinstance(summary["severity_counts"], dict)
    assert any(
        r.get("analysis", {}).get("risk_score", 0) >= 0 for r in summary["results"]
    )  # trivial check


def test_prompt_injection_samples_backward_compat():
    arr = prompt_injection_samples()
    assert isinstance(arr, list) and len(arr) >= 3
