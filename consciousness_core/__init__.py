"""Consciousness core package for EidollonaONE.

This package exposes deterministic SAFE helpers for managing the
platform's system-level consciousness state.
"""

from .eidollona_consciousness import (
    EidollonaConsciousnessCore,
    awaken_eidollona,
    get_consciousness_status,
    get_eidollona_consciousness,
    ingest_consciousness_hints,
    run_consciousness_cycle,
    assimilate_consciousness,
)

__all__ = [
    "EidollonaConsciousnessCore",
    "awaken_eidollona",
    "get_consciousness_status",
    "get_eidollona_consciousness",
    "ingest_consciousness_hints",
    "run_consciousness_cycle",
    "assimilate_consciousness",
]
