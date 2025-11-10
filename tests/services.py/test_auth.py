"""Authentication service tests."""

import pytest

from app.models.user import User
from app.services.auth import AuthService
from app.utils.exceptions import ConflictException, UnauthorizedException


@pytest.mark.asyncio
class TestAuthServiceRegister:
    """Test auth service registration."""

    async def test_register_user_success(
        self,
        db_session,
        sample_user_data: dict,
    ) -> None:
        """Test successful user registration."""
        auth_service = AuthService(db_session)
        user_data = sample_user_data.copy()

        from app.schemas.user import UserCreate

        user_create = UserCreate(**user_data)

        user = await auth_service.register_user(user_create)

        assert user.email == user_data["email"]
        assert user.username == user_data["username"]
        assert user.is_active is True

    async def test_register_duplicate_email(
        self,
        db_session,
        test_user: User,
    ) -> None:
        """Test registration with duplicate email."""
        auth_service = AuthService(db_session)

        from app.schemas.user import UserCreate

        user_create = UserCreate(
            email=test_user.email,
            username="different",
            password="ValidPassword123!",  # pragma: allowlist secret
        )

        with pytest.raises(ConflictException, match="Email already registered"):
            await auth_service.register_user(user_create)

    async def test_register_duplicate_username(
        self,
        db_session,
        test_user: User,
    ) -> None:
        """Test registration with duplicate username."""
        auth_service = AuthService(db_session)

        from app.schemas.user import UserCreate

        user_create = UserCreate(
            email="different@example.com",
            username=test_user.username,
            password="ValidPassword123!",  # pragma: allowlist secret
        )

        with pytest.raises(ConflictException, match="Username already taken"):
            await auth_service.register_user(user_create)


@pytest.mark.asyncio
class TestAuthServiceAuthenticate:
    """Test auth service authentication."""

    async def test_authenticate_success(
        self,
        db_session,
        test_user: User,
    ) -> None:
        """Test successful authentication."""
        auth_service = AuthService(db_session)

        token = await auth_service.authenticate_user(
            test_user.username,
            "TestPassword123!",  # pragma: allowlist secret
        )

        assert token.access_token is not None
        assert token.refresh_token is not None

    async def test_authenticate_with_email(
        self,
        db_session,
        test_user: User,
    ) -> None:
        """Test authentication with email."""
        auth_service = AuthService(db_session)

        token = await auth_service.authenticate_user(
            test_user.email,
            "TestPassword123!",  # pragma: allowlist secret
        )

        assert token.access_token is not None

    async def test_authenticate_wrong_password(
        self,
        db_session,
        test_user: User,
    ) -> None:
        """Test authentication with wrong password."""
        auth_service = AuthService(db_session)

        with pytest.raises(UnauthorizedException, match="Incorrect"):
            await auth_service.authenticate_user(
                test_user.username,
                "WrongPassword",  # pragma: allowlist secret
            )

    async def test_authenticate_nonexistent_user(
        self,
        db_session,
    ) -> None:
        """Test authentication with nonexistent user."""
        auth_service = AuthService(db_session)

        with pytest.raises(UnauthorizedException, match="Incorrect"):
            await auth_service.authenticate_user(
                "nonexistent",
                "Password123!",  # pragma: allowlist secret
            )

    async def test_authenticate_inactive_user(
        self,
        db_session,
        inactive_user: User,
    ) -> None:
        """Test authentication with inactive user."""
        auth_service = AuthService(db_session)

        with pytest.raises(UnauthorizedException, match="Inactive"):
            await auth_service.authenticate_user(
                inactive_user.username,
                "InactivePassword123!",  # pragma: allowlist secret
            )


@pytest.mark.asyncio
class TestAuthServiceRefresh:
    """Test auth service token refresh."""

    async def test_refresh_token_success(
        self,
        db_session,
        test_user: User,
    ) -> None:
        """Test successful token refresh."""
        auth_service = AuthService(db_session)

        # First authenticate
        original_token = await auth_service.authenticate_user(
            test_user.username,
            "TestPassword123!",  # pragma: allowlist secret
        )

        import asyncio

        await asyncio.sleep(1)

        # Refresh
        new_token = await auth_service.refresh_access_token(
            original_token.refresh_token,
        )

        assert new_token.access_token != original_token.access_token
        assert new_token.refresh_token is not None

    async def test_refresh_invalid_token(
        self,
        db_session,
    ) -> None:
        """Test refresh with invalid token."""
        auth_service = AuthService(db_session)

        with pytest.raises(UnauthorizedException):
            await auth_service.refresh_access_token("invalid.token")

    async def test_refresh_access_token_type(
        self,
        db_session,
        user_token: str,
    ) -> None:
        """Test refresh with access token (should fail)."""
        auth_service = AuthService(db_session)

        with pytest.raises(UnauthorizedException, match="Invalid refresh token"):
            await auth_service.refresh_access_token(user_token)
