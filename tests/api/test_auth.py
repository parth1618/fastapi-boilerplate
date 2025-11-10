"""Authentication endpoint tests."""

import pytest
from httpx import AsyncClient

from app.models.user import User


def get_error_message(response_json: dict) -> str:
    """Extract error message from response, handling both old and new formats."""
    if "error" in response_json:
        return response_json["error"]["message"]
    return response_json.get("detail", "")


def get_validation_errors(response_json: dict) -> list:
    """Extract validation errors from response."""
    if "error" in response_json and "details" in response_json["error"]:
        return response_json["error"]["details"].get("errors", [])
    return response_json.get("detail", [])


@pytest.mark.asyncio
class TestUserRegistration:
    """Test user registration endpoint."""

    async def test_register_user_success(
        self,
        client: AsyncClient,
        sample_user_data: dict,
    ) -> None:
        """Test successful user registration."""
        response = await client.post("/api/v1/auth/register", json=sample_user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["username"] == sample_user_data["username"]
        assert "id" in data
        assert "hashed_password" not in data
        assert data["is_active"] is True
        assert data["is_superuser"] is False

    async def test_register_duplicate_email(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test registration with duplicate email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "username": "differentuser",
                "password": "ValidPassword123!",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 409
        error_msg = get_error_message(response.json())
        assert "already registered" in error_msg.lower()

    async def test_register_duplicate_username(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test registration with duplicate username."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "different@example.com",
                "username": test_user.username,
                "password": "ValidPassword123!",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 409
        error_msg = get_error_message(response.json())
        assert "already taken" in error_msg.lower()

    async def test_register_weak_password(
        self,
        client: AsyncClient,
        weak_password_data: dict,
    ) -> None:
        """Test registration with weak password."""
        response = await client.post("/api/v1/auth/register", json=weak_password_data)

        assert response.status_code == 422
        errors = get_validation_errors(response.json())
        assert any("password" in str(error).lower() for error in errors)

    async def test_register_invalid_email(
        self,
        client: AsyncClient,
        invalid_email_data: dict,
    ) -> None:
        """Test registration with invalid email."""
        response = await client.post("/api/v1/auth/register", json=invalid_email_data)

        assert response.status_code == 422
        errors = get_validation_errors(response.json())
        assert any("email" in str(error).lower() for error in errors)

    async def test_register_reserved_username(
        self,
        client: AsyncClient,
        reserved_username_data: dict,
    ) -> None:
        """Test registration with reserved username."""
        response = await client.post("/api/v1/auth/register", json=reserved_username_data)

        assert response.status_code == 422
        errors = get_validation_errors(response.json())
        assert any("reserved" in str(error).lower() for error in errors)

    async def test_register_missing_fields(self, client: AsyncClient) -> None:
        """Test registration with missing required fields."""
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 422
        errors = get_validation_errors(response.json())
        assert len(errors) > 0


@pytest.mark.asyncio
class TestUserLogin:
    """Test user login endpoint."""

    async def test_login_success(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "TestPassword123!",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    async def test_login_with_email(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test login with email instead of username."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "TestPassword123!",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_login_invalid_password(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test login with invalid password."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "WrongPassword123!",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 401
        error_msg = get_error_message(response.json())
        assert "incorrect" in error_msg.lower()

    async def test_login_nonexistent_user(self, client: AsyncClient) -> None:
        """Test login with nonexistent user."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent",
                "password": "Password123!",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 401
        error_msg = get_error_message(response.json())
        assert "incorrect" in error_msg.lower()

    async def test_login_inactive_user(
        self,
        client: AsyncClient,
        inactive_user: User,
    ) -> None:
        """Test login with inactive user."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": inactive_user.username,
                "password": "InactivePassword123!",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 401
        error_msg = get_error_message(response.json())
        assert "inactive" in error_msg.lower()

    async def test_login_missing_credentials(self, client: AsyncClient) -> None:
        """Test login with missing credentials."""
        response = await client.post("/api/v1/auth/login", data={})

        assert response.status_code == 422


@pytest.mark.asyncio
class TestTokenRefresh:
    """Test token refresh endpoint."""

    async def test_refresh_token_success(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test successful token refresh."""
        # First login
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "TestPassword123!",
            },  # pragma: allowlist secret
        )
        original_tokens = login_response.json()
        refresh_token = original_tokens["refresh_token"]

        # Add small delay to ensure different token timestamps
        import asyncio

        await asyncio.sleep(1)

        # Refresh token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # Note: Depending on implementation, tokens might be the same or different
        # Just verify they exist and are valid format

    async def test_refresh_with_invalid_token(self, client: AsyncClient) -> None:
        """Test refresh with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401

    async def test_refresh_with_expired_token(
        self,
        client: AsyncClient,
        expired_token: str,
    ) -> None:
        """Test refresh with expired token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_token},
        )

        assert response.status_code == 401

    async def test_refresh_with_access_token(
        self,
        client: AsyncClient,
        user_token: str,
    ) -> None:
        """Test refresh with access token (should fail)."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": user_token},
        )

        assert response.status_code == 401

    async def test_refresh_missing_token(self, client: AsyncClient) -> None:
        """Test refresh without token."""
        response = await client.post("/api/v1/auth/refresh", json={})

        assert response.status_code == 422
