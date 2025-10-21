"""Minimal trace API used by the project.

This shim mimics the handful of functions and classes accessed within
`observability.otel_boot` to keep optional OpenTelemetry integration
from crashing when the dependency is absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

_tracer_provider: Optional["TracerProvider"] = None


@dataclass
class Span:
    """No-op span implementation."""

    recording: bool = False

    def is_recording(self) -> bool:
        return self.recording

    def set_attribute(self, key: str, value) -> None:  # pragma: no cover - no-op
        return None


_current_span: Span = Span(recording=False)


class TracerProvider:
    """Simple container tracked by the shim."""

    def __init__(self, resource=None) -> None:
        self.resource = resource
        self._processors = []

    def add_span_processor(self, processor) -> None:  # pragma: no cover - no-op
        self._processors.append(processor)


def get_tracer_provider() -> Optional[TracerProvider]:
    return _tracer_provider


def set_tracer_provider(provider: TracerProvider) -> None:
    global _tracer_provider
    _tracer_provider = provider


def get_current_span() -> Span:
    return _current_span


__all__ = [
    "Span",
    "TracerProvider",
    "get_tracer_provider",
    "set_tracer_provider",
    "get_current_span",
]
