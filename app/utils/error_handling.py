"""Enterprise-grade error handling system."""

import sys
import traceback
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import (
    DatabaseError,
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
)
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.utils.exceptions import AppException

logger = structlog.get_logger()


class ErrorResponse:
    """Standardized error response format."""

    def __init__(
        self,
        error_code: str,
        message: str,
        details: dict[str, Any] | None = None,
        status_code: int = 500,
    ) -> None:
        """Initialize error response.

        Args:
            error_code: Machine-readable error code
            message: Human-readable error message
            details: Additional error details
            status_code: HTTP status code
        """
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.status_code = status_code

    def to_dict(self, include_traceback: bool = False) -> dict[str, Any]:
        """Convert to dictionary format.

        Args:
            include_traceback: Whether to include traceback (dev only)

        Returns:
            dict: Error response dictionary
        """
        response = {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            }
        }

        if include_traceback and settings.DEBUG:
            _, _, exc_traceback = sys.exc_info()
            if exc_traceback:
                response["error"]["traceback"] = traceback.format_tb(exc_traceback)

        return response


def serialize_error_detail(error: dict[str, Any]) -> dict[str, Any]:
    """Serialize error detail ensuring all values are JSON serializable.

    Args:
        error: Error dictionary from Pydantic validation

    Returns:
        dict: Serializable error dictionary
    """
    serialized: dict[str, Any] = {}
    for key, value in error.items():
        if isinstance(value, (str, int, float, bool, type(None))):
            serialized[key] = value
        elif isinstance(value, (list, tuple)):
            serialized[key] = [str(item) for item in value]
        elif isinstance(value, dict):
            serialized[key] = serialize_error_detail(value)
        else:
            serialized[key] = str(value)
    return serialized


def setup_exception_handlers(app: FastAPI) -> None:  # noqa: PLR0915
    """Set up comprehensive exception handlers for the application.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ) -> JSONResponse:
        """Handle custom application exceptions."""
        logger.error(
            "application_error",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            path=request.url.path,
            method=request.method,
            extra=exc.extra,
        )

        error_response = ErrorResponse(
            error_code=exc.error_code or "APP_ERROR",
            message=exc.message,
            details=exc.extra,
            status_code=exc.status_code,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.to_dict(include_traceback=settings.DEBUG),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        errors = exc.errors()

        # Format validation errors with proper serialization
        formatted_errors = []
        for error in errors:
            # Convert error dict to plain dict for serialization
            error_dict = dict(error)
            serialized_error = serialize_error_detail(error_dict)
            formatted_errors.append(
                {
                    "field": ".".join(str(x) for x in error["loc"]),
                    "message": serialized_error.get("msg", str(error.get("msg", ""))),
                    "type": serialized_error.get("type", str(error.get("type", ""))),
                }
            )

        logger.warning(
            "validation_error",
            errors=formatted_errors,
            path=request.url.path,
            method=request.method,
        )

        error_response = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": formatted_errors},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=error_response.to_dict(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        logger.warning(
            "http_error",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
            method=request.method,
        )

        error_response = ErrorResponse(
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            status_code=exc.status_code,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.to_dict(),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request,
        exc: IntegrityError,
    ) -> JSONResponse:
        """Handle database integrity errors (unique constraints, etc.)."""
        logger.error(
            "database_integrity_error",
            error=str(exc),
            path=request.url.path,
            method=request.method,
        )

        # Parse common integrity errors
        error_message = "Database constraint violation"
        if "unique constraint" in str(exc).lower():
            error_message = "A record with this value already exists"
        elif "foreign key constraint" in str(exc).lower():
            error_message = "Referenced record does not exist"
        elif "not null constraint" in str(exc).lower():
            error_message = "Required field is missing"

        error_response = ErrorResponse(
            error_code="DATABASE_INTEGRITY_ERROR",
            message=error_message,
            details={"database_error": str(exc) if settings.DEBUG else None},
            status_code=status.HTTP_409_CONFLICT,
        )

        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_response.to_dict(),
        )

    @app.exception_handler(OperationalError)
    async def operational_error_handler(
        request: Request,
        exc: OperationalError,
    ) -> JSONResponse:
        """Handle database operational errors (connection issues, etc.)."""
        logger.error(
            "database_operational_error",
            error=str(exc),
            path=request.url.path,
            method=request.method,
        )

        error_response = ErrorResponse(
            error_code="DATABASE_UNAVAILABLE",
            message="Database service temporarily unavailable",
            details={"error": str(exc) if settings.DEBUG else None},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response.to_dict(),
        )

    @app.exception_handler(DatabaseError)
    async def database_error_handler(
        request: Request,
        exc: DatabaseError,
    ) -> JSONResponse:
        """Handle general database errors."""
        logger.error(
            "database_error",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method,
        )

        error_response = ErrorResponse(
            error_code="DATABASE_ERROR",
            message="A database error occurred",
            details={"error": str(exc) if settings.DEBUG else None},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.to_dict(),
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(
        request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        """Handle SQLAlchemy errors."""
        logger.error(
            "sqlalchemy_error",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method,
        )

        error_response = ErrorResponse(
            error_code="DATABASE_ERROR",
            message="A database operation failed",
            details={"error": str(exc) if settings.DEBUG else None},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.to_dict(),
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_error_handler(
        request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        errors = exc.errors()

        # Serialize errors properly - convert to dict first
        serialized_errors = [serialize_error_detail(dict(error)) for error in errors]

        logger.warning(
            "pydantic_validation_error",
            errors=serialized_errors,
            path=request.url.path,
            method=request.method,
        )

        error_response = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Data validation failed",
            details={"errors": serialized_errors},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=error_response.to_dict(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle all unhandled exceptions."""
        logger.error(
            "unhandled_exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method,
            exc_info=True,
        )

        # Don't expose internal errors in production
        message = str(exc) if settings.DEBUG else "An internal error occurred"

        error_response = ErrorResponse(
            error_code="INTERNAL_ERROR",
            message=message,
            details={"error_type": type(exc).__name__ if settings.DEBUG else None},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.to_dict(include_traceback=settings.DEBUG),
        )


# Error tracking and alerting
class ErrorTracker:
    """Track and aggregate errors for monitoring."""

    def __init__(self) -> None:
        """Initialize error tracker."""
        self.error_counts: dict[str, int] = {}
        self.error_samples: dict[str, list[str]] = {}

    def track_error(self, error_code: str, error_message: str) -> None:
        """Track an error occurrence.

        Args:
            error_code: Error code
            error_message: Error message
        """
        # Increment counter
        self.error_counts[error_code] = self.error_counts.get(error_code, 0) + 1

        # Store sample (keep last 10)
        if error_code not in self.error_samples:
            self.error_samples[error_code] = []

        self.error_samples[error_code].append(error_message)
        if len(self.error_samples[error_code]) > 10:
            self.error_samples[error_code].pop(0)

        # Alert if error threshold exceeded
        if self.error_counts[error_code] > 100:
            self._trigger_alert(error_code)

    def _trigger_alert(self, error_code: str) -> None:
        """Trigger alert for high error count.

        Args:
            error_code: Error code that exceeded threshold
        """
        logger.critical(
            "error_threshold_exceeded",
            error_code=error_code,
            count=self.error_counts[error_code],
            samples=self.error_samples.get(error_code, []),
        )
        # Implement alerting logic (email, Slack, PagerDuty, etc.)

    def get_stats(self) -> dict[str, Any]:
        """Get error statistics.

        Returns:
            dict: Error statistics
        """
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts": self.error_counts,
            "top_errors": sorted(
                self.error_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10],
        }


# Global error tracker instance
error_tracker = ErrorTracker()
