"""Prometheus metrics for monitoring."""

import time
from collections.abc import Awaitable, Callable

import structlog
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

logger = structlog.get_logger()

# Define metrics
REQUEST_COUNT = Counter(
    "fastapi_requests_total",
    "Total request count",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "fastapi_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
)

REQUEST_IN_PROGRESS = Gauge(
    "fastapi_requests_in_progress",
    "Requests in progress",
    ["method", "endpoint"],
)

ACTIVE_CONNECTIONS = Gauge(
    "fastapi_active_connections",
    "Number of active connections",
)

DATABASE_CONNECTIONS = Gauge(
    "fastapi_database_connections",
    "Number of database connections",
)

CACHE_HITS = Counter(
    "fastapi_cache_hits_total",
    "Total cache hits",
)

CACHE_MISSES = Counter(
    "fastapi_cache_misses_total",
    "Total cache misses",
)

ERROR_COUNT = Counter(
    "fastapi_errors_total",
    "Total error count",
    ["error_type", "endpoint"],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and collect metrics."""
        if not settings.METRICS_ENABLED:
            return await call_next(request)

        # Skip metrics endpoint
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = request.url.path

        # Increment in-progress counter
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=path).inc()
        ACTIVE_CONNECTIONS.inc()

        start_time = time.time()

        try:
            # Process request
            response: Response = await call_next(request)

            # Record duration
            duration = time.time() - start_time
            REQUEST_DURATION.labels(method=method, endpoint=path).observe(duration)

            # Record request count
            REQUEST_COUNT.labels(method=method, endpoint=path, status=response.status_code).inc()

            return response

        except Exception as e:
            # Record error
            ERROR_COUNT.labels(error_type=type(e).__name__, endpoint=path).inc()
            raise

        finally:
            # Decrement in-progress counter
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=path).dec()
            ACTIVE_CONNECTIONS.dec()


def metrics_endpoint() -> Response:
    """Expose Prometheus metrics endpoint."""
    metrics_data = generate_latest()
    return Response(
        content=metrics_data,
        media_type="text/plain",
    )


def track_cache_hit() -> None:
    """Track cache hit."""
    if settings.METRICS_ENABLED:
        CACHE_HITS.inc()


def track_cache_miss() -> None:
    """Track cache miss."""
    if settings.METRICS_ENABLED:
        CACHE_MISSES.inc()


def track_error(error_type: str, endpoint: str) -> None:
    """Track error occurrence."""
    if settings.METRICS_ENABLED:
        ERROR_COUNT.labels(error_type=error_type, endpoint=endpoint).inc()


def update_database_connections(count: int) -> None:
    """Update database connection count."""
    if settings.METRICS_ENABLED:
        DATABASE_CONNECTIONS.set(count)
