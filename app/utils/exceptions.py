"""Custom exceptions."""

from typing import Any


class AppException(Exception):  # noqa: N818
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Initialize exception."""
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.extra = extra or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    """Resource not found exception."""

    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        """Initialize exception."""
        super().__init__(message, status_code=404, error_code="NOT_FOUND", **kwargs)


class UnauthorizedException(AppException):
    """Unauthorized exception."""

    def __init__(self, message: str = "Unauthorized", **kwargs: Any) -> None:
        """Initialize exception."""
        super().__init__(message, status_code=401, error_code="UNAUTHORIZED", **kwargs)


class ForbiddenException(AppException):
    """Forbidden exception."""

    def __init__(self, message: str = "Forbidden", **kwargs: Any) -> None:
        """Initialize exception."""
        super().__init__(message, status_code=403, error_code="FORBIDDEN", **kwargs)


class BadRequestException(AppException):
    """Bad request exception."""

    def __init__(self, message: str = "Bad request", **kwargs: Any) -> None:
        """Initialize exception."""
        super().__init__(message, status_code=400, error_code="BAD_REQUEST", **kwargs)


class ConflictException(AppException):
    """Conflict exception."""

    def __init__(self, message: str = "Resource already exists", **kwargs: Any) -> None:
        """Initialize exception."""
        super().__init__(message, status_code=409, error_code="CONFLICT", **kwargs)
