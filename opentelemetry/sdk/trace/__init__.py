"""Shim tracer provider that reuses the core no-op implementation."""

from __future__ import annotations

from opentelemetry.trace import TracerProvider as _BaseTracerProvider


class TracerProvider(_BaseTracerProvider):
    def __init__(self, resource=None) -> None:
        super().__init__(resource=resource)


__all__ = ["TracerProvider"]
