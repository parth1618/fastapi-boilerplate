"""Enhanced FastAPI application entry point with production features."""

import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import api_router
from app.core.config import settings, validate_configuration
from app.core.events import on_shutdown, on_startup
from app.core.telemetry import setup_telemetry
from app.middleware.cors import setup_cors
from app.middleware.logging import LoggingMiddleware
from app.middleware.metrics import PrometheusMiddleware
from app.middleware.rate_limit import limiter
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.validation import InputValidationMiddleware
from app.utils.error_handling import setup_exception_handlers

logger = structlog.get_logger()


# Application Lifespan Management


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events.

    Handles:
    - Configuration validation
    - Database initialization
    - Cache initialization
    - Background task startup
    - Resource cleanup on shutdown
    """
    # Startup
    try:
        logger.info(
            "application_startup_initiated",
            environment=settings.ENVIRONMENT,
            version=settings.VERSION,
        )

        # Validate configuration
        config_warnings = validate_configuration()
        if config_warnings:
            for warning in config_warnings:
                logger.warning("configuration_warning", warning=warning)

        # Run startup tasks
        await on_startup(app)

        logger.info(
            "application_startup_complete",
            environment=settings.ENVIRONMENT,
            version=settings.VERSION,
        )

        yield

    except Exception as e:
        logger.critical(
            "application_startup_failed",
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        # Shutdown
        logger.info("application_shutdown_initiated")
        await on_shutdown(app)
        logger.info("application_shutdown_complete")


# Create Application Instance
def create_application() -> FastAPI:
    """Create and configure FastAPI application instance.

    Returns:
        FastAPI: Configured application instance
    """
    # Determine if docs should be enabled
    docs_url = settings.DOCS_URL if settings.DOCS_ENABLED else None
    redoc_url = settings.REDOC_URL if settings.DOCS_ENABLED else None
    openapi_url = settings.OPENAPI_URL if settings.DOCS_ENABLED else None

    # Create application
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Production-ready FastAPI backend boilerplate with enterprise features",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
        # Additional metadata
        contact={
            "name": "API Support",
            "url": str(settings.BACKEND_URL),
            "email": "support@example.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
    )

    # Add rate limiter state
    application.state.limiter = limiter

    return application


app = create_application()


# Security Middleware

# Trusted Host middleware (prevent host header attacks)
if settings.is_production:
    allowed_hosts = [
        str(settings.BACKEND_URL).split("://")[1].split("/")[0],
        str(settings.FRONTEND_URL).split("://")[1].split("/")[0],
    ]
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts,
    )

# Session middleware (if needed for OAuth, etc.)
if settings.FEATURE_SOCIAL_AUTH_ENABLED:
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.JWT_SECRET_KEY,
        session_cookie="session",
        max_age=settings.SESSION_TIMEOUT_MINUTES * 60,
        same_site="lax",
        https_only=settings.is_production,
    )

# Compression middleware
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  # Only compress responses > 1KB
    compresslevel=6,  # Balance between speed and compression
)


# Application Middleware


# Setup CORS
setup_cors(app)

# Setup OpenTelemetry (if enabled)
if settings.OTEL_ENABLED:
    setup_telemetry(app)

# Input validation middleware (must be early in chain)
app.add_middleware(
    InputValidationMiddleware,
    max_request_size=10 * 1024 * 1024,  # 10MB
)

# Request ID tracking
app.add_middleware(RequestIDMiddleware)

# Logging middleware
app.add_middleware(LoggingMiddleware)

# Metrics collection (if enabled)
if settings.METRICS_ENABLED:
    app.add_middleware(PrometheusMiddleware)


# Exception Handlers


# Setup comprehensive exception handlers
setup_exception_handlers(app)

# Rate limit exceeded handler
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,  # type: ignore
)


# Health Check Endpoints


@app.get(
    "/",
    tags=["Root"],
    summary="Root endpoint",
    description="Basic API information",
)
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": settings.DOCS_URL if settings.DOCS_ENABLED else "disabled",
        "status": "operational",
    }


@app.get(
    "/ping",
    tags=["Health"],
    summary="Simple ping endpoint",
    description="Quick health check without dependencies",
)
async def ping() -> dict[str, str]:
    """Simple ping endpoint for basic health check."""
    return {"status": "ok", "message": "pong"}


@app.get(
    "/version",
    tags=["Info"],
    summary="Get API version",
    description="Returns API version information",
)
async def version() -> dict[str, str]:
    """Get API version information."""
    return {
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }


# Include API v1 router
app.include_router(
    api_router,
    prefix=settings.API_V1_PREFIX,
)
