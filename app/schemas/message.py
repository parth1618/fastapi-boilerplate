"""Message Pydantic schemas."""

from typing import Any

from pydantic import BaseModel


class Message(BaseModel):
    """Generic message schema."""

    message: str


class HealthCheck(BaseModel):
    """Health check response schema."""

    status: str
    version: str
    environment: str
    database: str
    redis: str


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str
    error_code: str | None = None
    extra: dict[str, Any] | None = None
