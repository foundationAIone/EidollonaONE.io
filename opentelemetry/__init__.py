"""Lightweight OpenTelemetry shim for environments without the optional dependency.

This module provides the minimal surface area required by `observability.otel_boot`
so that static analysis and runtime calls do not fail when the real OpenTelemetry
package is unavailable. All operations are implemented as no-ops.
"""

from __future__ import annotations

from types import SimpleNamespace

from . import trace as trace_module

trace = SimpleNamespace(
    get_current_span=trace_module.get_current_span,
    set_tracer_provider=trace_module.set_tracer_provider,
    get_tracer_provider=trace_module.get_tracer_provider,
)

__all__ = ["trace"]
