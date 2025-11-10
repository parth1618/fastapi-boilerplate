"""Configuration tests."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


class TestSettingsValidation:
    """Test settings validation."""

    def test_jwt_secret_min_length(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test JWT secret minimum length validation."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET_KEY", "short")

        with pytest.raises(ValidationError, match="at least 32"):
            Settings()

    def test_production_debug_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test DEBUG must be False in production."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("FRONTEND_URL", "https://example.com")

        with pytest.raises(ValidationError, match="DEBUG must be False"):
            Settings()

    def test_production_https_required(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test HTTPS required in production."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("FRONTEND_URL", "http://example.com")

        with pytest.raises(ValidationError, match="HTTPS"):
            Settings()

    def test_weak_jwt_secret_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test weak JWT secret rejected in production."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-in-production")
        monkeypatch.setenv("FRONTEND_URL", "https://example.com")

        with pytest.raises(ValidationError, match="default value"):
            Settings()

    def test_cors_origins_parsing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test CORS origins parsing from string."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")

        settings = Settings()
        assert len(settings.CORS_ORIGINS) == 2
        assert "http://localhost:3000" in settings.CORS_ORIGINS

    def test_database_url_sync_property(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test database_url_sync property."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)

        settings = Settings()
        assert "+asyncpg" not in settings.database_url_sync
        assert "postgresql://" in settings.database_url_sync

    def test_is_production_property(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test is_production property."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("FRONTEND_URL", "https://example.com")

        settings = Settings()
        assert settings.is_production is True

    def test_get_settings_cached(self) -> None:
        """Test settings caching."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2
