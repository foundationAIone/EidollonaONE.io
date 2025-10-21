"""Thin shim around the global audit logger to keep symbolic_core self-contained."""

from __future__ import annotations

from typing import Any

try:  # Prefer the shared audit module when available
    from utils.audit import audit_ndjson as _delegate
except Exception:  # pragma: no cover - test environments may lack audit plumbing
    def _delegate(event: str, **payload: Any) -> None:
        """Fallback to a no-op so symbolic_core remains importable."""
        # Intentionally silent: diagnostics rely on audit sink being optional.
        return


def audit_ndjson(event: str, **payload: Any) -> None:
    """Proxy that forwards to the shared audit logger when present."""
    _delegate(event, **payload)


__all__ = ["audit_ndjson"]
