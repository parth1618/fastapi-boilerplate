"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

# Create test session factory
TestAsyncSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with TestAsyncSessionLocal() as session:
        yield session

    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("TestPassword123!"),
        is_active=True,
        is_superuser=False,
        role="user",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create test admin user."""
    admin = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password=get_password_hash("AdminPassword123!"),
        is_active=True,
        is_superuser=True,
        role="admin",
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def inactive_user(db_session: AsyncSession) -> User:
    """Create inactive test user."""
    user = User(
        email="inactive@example.com",
        username="inactiveuser",
        full_name="Inactive User",
        hashed_password=get_password_hash("InactivePassword123!"),
        is_active=False,
        is_superuser=False,
        role="user",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def user_token(test_user: User) -> str:
    """Create access token for test user."""
    return create_access_token(subject=test_user.id)


@pytest.fixture
def admin_token(test_admin: User) -> str:
    """Create access token for test admin."""
    return create_access_token(subject=test_admin.id)


@pytest.fixture
def expired_token() -> str:
    """Create expired token."""
    from datetime import datetime, timedelta, timezone

    import jwt

    from app.core.config import settings

    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {"exp": expire, "sub": "999", "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def invalid_token() -> str:
    """Create invalid token."""
    return "invalid.token.here"


@pytest.fixture
def auth_headers(user_token: str) -> dict[str, str]:
    """Create authorization headers for test user."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    """Create authorization headers for test admin."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Sample valid user data."""
    return {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "NewPassword123!",  # pragma: allowlist secret
        "full_name": "New User",
    }


@pytest.fixture
def weak_password_data() -> dict[str, Any]:
    """Sample data with weak password."""
    return {
        "email": "weak@example.com",
        "username": "weakuser",
        "password": "weak",  # pragma: allowlist secret
    }


@pytest.fixture
def invalid_email_data() -> dict[str, Any]:
    """Sample data with invalid email."""
    return {
        "email": "not-an-email",
        "username": "validuser",
        "password": "ValidPassword123!",  # pragma: allowlist secret
    }


@pytest.fixture
def reserved_username_data() -> dict[str, Any]:
    """Sample data with reserved username."""
    return {
        "email": "reserved@example.com",
        "username": "admin",
        "password": "ValidPassword123!",  # pragma: allowlist secret
    }
