"""Legacy wrapper re-exporting sensing gatekeeper shim."""

from __future__ import annotations

from . import GateDecision, Gatekeeper

__all__ = ["GateDecision", "Gatekeeper"]
