"""Initialize database with default data."""

import os
import secrets

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User

logger = structlog.get_logger()


async def init_db(db: AsyncSession) -> None:
    """Initialize database with default admin user.

    Security:
    - PRODUCTION: Requires INITIAL_ADMIN_PASSWORD env var (min 32 chars)
    - DEVELOPMENT: Auto-generates secure password if not provided
    - Never logs passwords in production
    - Validates email format
    """
    environment = os.getenv("ENVIRONMENT", "development")
    is_production = environment == "production"

    # Check if admin exists
    result = await db.execute(select(User).where(User.email == "admin@example.com"))
    existing_admin = result.scalar_one_or_none()

    if existing_admin:
        logger.info("admin_user_already_exists", user_id=existing_admin.id)
        return

    # Get or generate admin password
    admin_password: str | None = os.getenv("INITIAL_ADMIN_PASSWORD")

    if not admin_password:
        if is_production:
            raise RuntimeError(
                "CRITICAL: INITIAL_ADMIN_PASSWORD environment variable is REQUIRED in production. "
                "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        admin_password = secrets.token_urlsafe(32)  # Development: Auto-generate
        logger.warning(
            "admin_password_auto_generated",
            password=admin_password,
            message="⚠️  SAVE THIS PASSWORD - It will not be shown again!",
        )

    # Validate password strength
    if len(admin_password) < 32:
        raise ValueError(
            f"INITIAL_ADMIN_PASSWORD must be at least 32 characters (got {len(admin_password)}). "
            "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )

    # Get admin credentials from environment
    admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com")
    admin_username = os.getenv("INITIAL_ADMIN_USERNAME", "admin")

    # Validate email format
    if "@" not in admin_email:
        raise ValueError(f"Invalid INITIAL_ADMIN_EMAIL format: {admin_email}")

    # Create admin user
    admin_user = User(
        email=admin_email,
        username=admin_username,
        full_name="System Administrator",
        hashed_password=get_password_hash(admin_password),
        is_active=True,
        is_superuser=True,
        role="admin",
    )

    db.add(admin_user)
    await db.commit()
    await db.refresh(admin_user)

    # Log creation (never log password in production)
    if is_production:
        logger.info(
            "admin_user_created",
            user_id=admin_user.id,
            email=admin_email,
            username=admin_username,
            message="Admin user created - password was provided via INITIAL_ADMIN_PASSWORD",
        )
    else:
        logger.info(
            "admin_user_created",
            user_id=admin_user.id,
            email=admin_email,
            username=admin_username,
            password=admin_password,
            message="DEVELOPMENT MODE: Admin password logged for convenience",
        )


async def main() -> None:
    """Run database initialization."""
    from app.db.session import db_manager

    # Initialize the database manager first
    db_manager.init()

    # Use the session context manager
    async with db_manager.session() as db:
        try:
            await init_db(db)
            print("✅ Database initialized successfully!")
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            raise
        finally:
            # Clean up database connections
            await db_manager.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
