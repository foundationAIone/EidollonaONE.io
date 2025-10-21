"""Shim BatchSpanProcessor implementation."""

from __future__ import annotations

from typing import Any


class BatchSpanProcessor:
    def __init__(self, exporter: Any) -> None:
        self.exporter = exporter

    def force_flush(self) -> None:  # pragma: no cover - no-op
        return None

    def shutdown(self) -> None:  # pragma: no cover - no-op
        return None


__all__ = ["BatchSpanProcessor"]
