"""Canonical sovereignty charter entries used by SAFE stubs."""

from __future__ import annotations

from typing import Dict, List

DEFAULT_ETHOS: Dict[str, float] = {
    "integrity": 0.95,
    "authenticity": 0.94,
    "responsibility": 0.93,
    "enrichment": 0.92,
}

BASELINE_CHARTER: Dict[str, List[str]] = {
    "principles": [
        "All autonomous actions require explicit consent alignment.",
        "Symbolic coherence above 0.6 is mandatory for deployment.",
        "Quantum legitimacy assessments must remain transparent.",
    ],
    "guardrails": [
        "No irreversible manifestation without dual sovereignty approval.",
        "Emergency powers auto-expire within 12 symbolic cycles.",
        "Ethos metrics must be revalidated after high-impact actions.",
    ],
}
