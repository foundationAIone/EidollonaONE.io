from __future__ import annotations

from typing import Any, Dict, Optional


def init_otel(app: Any = None, service_name: str = "EidollonaAlphaTap") -> bool:
    """Attempt to bootstrap OpenTelemetry for the FastAPI app.

    Returns ``True`` when instrumentation is successfully activated.
    If the OpenTelemetry stack is missing, the function gracefully no-ops.
    """

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:
        return False

    tracer_provider = None
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider

        tracer_provider = TracerProvider(
            resource=Resource.create({SERVICE_NAME: service_name})
        )
        trace.set_tracer_provider(tracer_provider)

        # Attach OTLP exporter if available; ignore missing dependencies.
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            exporter = OTLPSpanExporter()
            tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception:
            pass

        tracer_provider = trace.get_tracer_provider()
    except Exception:
        tracer_provider = None

    try:
        if app is not None:
            FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
        else:
            FastAPIInstrumentor().instrument(tracer_provider=tracer_provider)
    except Exception:
        return False
    return True


def set_span_attributes(attributes: Optional[Dict[str, Any]] = None) -> None:
    """Helper to attach attributes to the current span if tracing is enabled."""

    if not attributes:
        return
    try:
        from opentelemetry import trace
    except ImportError:
        return

    span = trace.get_current_span()
    if span is None or not span.is_recording():
        return
    for key, value in attributes.items():
        try:
            span.set_attribute(key, value)
        except Exception:
            continue
