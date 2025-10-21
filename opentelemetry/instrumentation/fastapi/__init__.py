"""Minimal FastAPI instrumentor shim.

The real OpenTelemetry package exposes a `FastAPIInstrumentor` with
`instrument_app` and `instrument` helpers. We supply compatible no-op
implementations so the optional observability bootstrap can succeed in
dev/test environments where the dependency is not installed.
"""

from __future__ import annotations

from typing import Any, Optional


class FastAPIInstrumentor:
    def __init__(self) -> None:
        pass

    @staticmethod
    def instrument_app(app: Any, tracer_provider: Optional[Any] = None) -> None:  # pragma: no cover - no-op
        return None

    def instrument(self, tracer_provider: Optional[Any] = None) -> None:  # pragma: no cover - no-op
        return None


__all__ = ["FastAPIInstrumentor"]
