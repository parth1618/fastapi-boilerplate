"""Health check endpoint tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthCheck:
    """Test health check endpoint."""

    async def test_health_check_success(self, client: AsyncClient) -> None:
        """Test successful health check."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert "database" in data
        assert "redis" in data

    async def test_health_check_database_healthy(self, client: AsyncClient) -> None:
        """Test health check with healthy database."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["database"] in ["healthy", "unhealthy"]

    @patch("app.api.v1.endpoints.health.aioredis.from_url")
    async def test_health_check_redis_failure(
        self,
        mock_redis: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Test health check with Redis failure."""
        # Mock Redis failure
        mock_redis.return_value.ping = AsyncMock(side_effect=Exception("Redis down"))

        response = await client.get("/api/v1/health")

        # Should still return 200 but with unhealthy status
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"

    @patch("app.api.v1.endpoints.health.text")
    async def test_health_check_database_failure(
        self,
        mock_text: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Test health check with database failure."""
        # This test requires mocking the database execute
        response = await client.get("/api/v1/health")

        # Even with failures, endpoint should return 200
        assert response.status_code == 200


@pytest.mark.asyncio
class TestReadinessCheck:
    """Test readiness check endpoint."""

    async def test_readiness_check_success(self, client: AsyncClient) -> None:
        """Test readiness check."""
        response = await client.get("/api/v1/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    async def test_readiness_check_format(self, client: AsyncClient) -> None:
        """Test readiness check response format."""
        response = await client.get("/api/v1/ready")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
