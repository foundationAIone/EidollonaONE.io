"""EMP-Guard: defensive pulse risk management (simulation-only).

Provides posture reports, hardening checklists, drills, and ethos-safe rebind flow.
Token-gated; NDJSON audits; no real device control.
"""

from __future__ import annotations

__all__ = [
    "playbooks",
]

from . import playbooks
