"""Shim OTLP span exporter.

Provides the `OTLPSpanExporter` symbol referenced by the optional
OpenTelemetry bootstrap. The implementation is a no-op.
"""

from __future__ import annotations

from typing import Iterable


class OTLPSpanExporter:
    def export(self, spans: Iterable[object]) -> None:  # pragma: no cover - no-op
        return None

    def shutdown(self) -> None:  # pragma: no cover - no-op
        return None


__all__ = ["OTLPSpanExporter"]
