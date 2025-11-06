"""Authentication service layer."""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate
from app.utils.exceptions import ConflictException, UnauthorizedException

logger = structlog.get_logger()


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize service."""
        self.db = db

    async def register_user(self, user_data: UserCreate) -> User:
        """Register a new user."""
        # Check if email already exists
        result = await self.db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise ConflictException("Email already registered")

        # Check if username already exists
        result = await self.db.execute(select(User).where(User.username == user_data.username))
        if result.scalar_one_or_none():
            raise ConflictException("Username already taken")

        # Create new user
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=False,
            role="user",
        )

        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)

        logger.info("user_registered", user_id=db_user.id, email=db_user.email)
        return db_user

    async def authenticate_user(self, username: str, password: str) -> Token:
        """Authenticate user and return tokens."""
        # Find user by email or username
        result = await self.db.execute(
            select(User).where((User.email == username) | (User.username == username))
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning("authentication_failed", username=username, reason="user_not_found")
            raise UnauthorizedException("Incorrect username or password")

        if not verify_password(password, user.hashed_password):
            logger.warning("authentication_failed", username=username, reason="invalid_password")
            raise UnauthorizedException("Incorrect username or password")

        if not user.is_active:
            logger.warning("authentication_failed", username=username, reason="inactive_user")
            raise UnauthorizedException("Inactive user")

        # Create tokens
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)

        logger.info("user_authenticated", user_id=user.id, email=user.email)

        return Token(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, refresh_token: str) -> Token:
        """Refresh access token using refresh token."""
        try:
            payload = verify_token(refresh_token)

            if payload.get("type") != "refresh":
                raise UnauthorizedException("Invalid refresh token")

            user_id = int(payload["sub"])

            # Verify user exists and is active
            result = await self.db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user or not user.is_active:
                raise UnauthorizedException("Invalid refresh token")

            # Create new tokens
            access_token = create_access_token(subject=user.id)
            new_refresh_token = create_refresh_token(subject=user.id)

            logger.info("token_refreshed", user_id=user.id)

            return Token(access_token=access_token, refresh_token=new_refresh_token)

        except ValueError as e:
            logger.warning("token_refresh_failed", error=str(e))
            raise UnauthorizedException("Invalid refresh token") from e
