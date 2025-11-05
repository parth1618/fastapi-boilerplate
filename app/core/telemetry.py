"""OpenTelemetry tracing and metrics setup."""

import structlog
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import settings

logger = structlog.get_logger()


def setup_telemetry(app) -> None:  # type: ignore[no-untyped-def]
    """Configure OpenTelemetry tracing and metrics."""
    if not settings.OTEL_ENABLED:
        logger.info("opentelemetry_disabled")
        return

    try:
        # Create resource with service information
        resource = Resource.create(
            {
                "service.name": settings.OTEL_SERVICE_NAME,
                "service.version": settings.VERSION,
                "deployment.environment": settings.ENVIRONMENT,
            }
        )

        # Setup Tracing
        trace_provider = TracerProvider(resource=resource)

        # Add OTLP exporter (sends to otel-collector)
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True,  # Use insecure connection for local development
        )
        trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        trace.set_tracer_provider(trace_provider)

        # Setup Metrics
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                insecure=True,  # Use insecure connection for local development
            )
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)

        # Instrument SQLAlchemy
        from app.db.session import engine  # noqa: PLC0415

        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)

        # Instrument Redis
        RedisInstrumentor().instrument()

        logger.info(
            "opentelemetry_initialized",
            service_name=settings.OTEL_SERVICE_NAME,
            otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        )

    except Exception as e:
        logger.error("opentelemetry_setup_failed", error=str(e))
        # Don't fail application startup if telemetry fails


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance."""
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Get a meter instance."""
    return metrics.get_meter(name)
