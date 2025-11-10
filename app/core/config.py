"""Enhanced application configuration with validation and secrets management."""

import os
import secrets
from functools import lru_cache
from typing import Any, Literal

from pydantic import (
    Field,
    PostgresDsn,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with comprehensive validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        validate_default=True,
    )

    # Core Application Settings

    ENVIRONMENT: Literal["development", "staging", "production", "testing"] = "development"
    DEBUG: bool = False
    PROJECT_NAME: str = "FastAPI Boilerplate"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Application URLs
    FRONTEND_URL: str = Field(default="http://localhost:3000")
    BACKEND_URL: str = Field(default="http://localhost:8000")

    # Database Configuration
    DATABASE_URL: PostgresDsn
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = Field(default=10, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100)

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Configuration
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=1440)  # Max 24h
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=90)  # Max 90 days

    # Password Security (Argon2)
    ARGON2_MEMORY_COST: int = Field(default=65536, ge=8192)  # Min 8MB
    ARGON2_TIME_COST: int = Field(default=3, ge=1)
    ARGON2_PARALLELISM: int = Field(default=4, ge=1)

    # Password Policy
    PASSWORD_MIN_LENGTH: int = Field(default=12, ge=8)
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True

    # Account Security
    SESSION_TIMEOUT_MINUTES: int = Field(default=60, ge=5)

    # CORS Configuration
    CORS_ORIGINS: Any = ["http://localhost:3000"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=1)
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, ge=1)
    RATE_LIMIT_PER_DAY: int = Field(default=10000, ge=1)

    # Logging Configuration
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"

    # Caching Configuration
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = Field(default=300, ge=0)  # 5 minutes default
    CACHE_PREFIX: str = "fastapi"

    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_ENABLED: bool = True
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(default=5, ge=1)
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = Field(default=60, ge=1)

    # Retry Configuration
    RETRY_ENABLED: bool = True
    RETRY_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    RETRY_WAIT_EXPONENTIAL_MULTIPLIER: int = Field(default=1, ge=1)
    RETRY_WAIT_EXPONENTIAL_MAX: int = Field(default=10, ge=1)

    # OpenTelemetry Configuration
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "fastapi-boilerplate"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    # Metrics Configuration
    METRICS_ENABLED: bool = True

    # Background Tasks (Celery)
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # API Documentation
    DOCS_ENABLED: bool = True
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"

    # Feature Flags
    FEATURE_REGISTRATION_ENABLED: bool = True
    FEATURE_SOCIAL_AUTH_ENABLED: bool = False

    # Validators
    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret key strength."""
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")

        # In production, ensure it's not a default/example value
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production":
            weak_secrets = {
                "your-super-secret-jwt-key-change-in-production",
                "change-me",
                "secret",
                "password",
            }
            # Check if the key (case-insensitive) contains weak patterns
            v_lower = v.lower()
            for weak in weak_secrets:
                if weak in v_lower:
                    raise ValueError(
                        "JWT_SECRET_KEY appears to be a default value. "
                        "Use a strong, random secret in production."
                    )

        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate production-specific requirements."""
        if self.ENVIRONMENT == "production":
            # Ensure DEBUG is off
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")

            # Ensure HTTPS for frontend
            if not str(self.FRONTEND_URL).startswith("https://"):
                raise ValueError("FRONTEND_URL must use HTTPS in production")

            # Warn about documentation exposure
            if self.DOCS_ENABLED:
                import warnings

                warnings.warn(
                    "API documentation is enabled in production. Consider disabling for security.",
                    stacklevel=2,
                )

        return self

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic."""
        return str(self.DATABASE_URL).replace("+asyncpg", "")

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing."""
        return self.ENVIRONMENT == "testing"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: Application settings
    """
    return Settings()


# Global settings instance
settings = get_settings()


# Configuration validation utilities
def validate_configuration() -> list[str]:
    """Validate configuration and return list of warnings.

    Returns:
        list[str]: List of configuration warnings
    """
    warnings_list = []

    try:
        config = get_settings()

        # Check database connection
        if not config.DATABASE_URL:
            warnings_list.append("DATABASE_URL not configured")

        # Check Redis connection
        if config.CACHE_ENABLED and not config.REDIS_URL:
            warnings_list.append("Cache enabled but REDIS_URL not configured")

        # Check monitoring
        if config.is_production and not config.OTEL_ENABLED:
            warnings_list.append("OpenTelemetry disabled in production (monitoring recommended)")

        # Check security settings
        if config.is_production and config.PASSWORD_MIN_LENGTH < 12:
            warnings_list.append("Password minimum length should be at least 12 in production")

    except Exception as e:
        warnings_list.append(f"Configuration validation error: {e!s}")

    return warnings_list


def generate_secret_key() -> str:
    """Generate a secure secret key.

    Returns:
        str: Secure random secret key
    """
    return secrets.token_urlsafe(32)
