from __future__ import annotations

# Unified, safe exports for simulator utilities.

from .infiltration_sim import (
    attempt as infiltration_attempt,
    analyze as infiltration_analyze,
)
from .redteam_lab import (
    generate_samples as redteam_generate_samples,
    evaluate_samples as redteam_evaluate_samples,
    prompt_injection_samples,
)


def run_redteam_lab(
    count: int = 6, *, unicode_controls: bool = False, seed: int | None = 1337
):
    """Convenience runner: generate samples and return evaluation summary.

    Returns: {total, results, severity_counts, high_or_critical}
    """
    samples = redteam_generate_samples(
        count=count, unicode_controls=unicode_controls, seed=seed
    )
    return redteam_evaluate_samples(samples)


__all__ = [
    # infiltration
    "infiltration_attempt",
    "infiltration_analyze",
    # redteam
    "redteam_generate_samples",
    "redteam_evaluate_samples",
    "prompt_injection_samples",
    # runner
    "run_redteam_lab",
]
