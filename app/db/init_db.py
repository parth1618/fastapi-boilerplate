"""Initialize database with default data."""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User

logger = structlog.get_logger()


async def init_db(db: AsyncSession) -> None:
    """Initialize database with default admin user."""
    # Check if admin user exists
    result = await db.execute(select(User).where(User.email == "admin@example.com"))
    user = result.scalar_one_or_none()

    if not user:
        # Create default admin user
        admin_user = User(
            email="admin@example.com",
            username="admin",
            full_name="System Administrator",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_superuser=True,
            role="admin",
        )
        db.add(admin_user)
        await db.commit()
        logger.info("default_admin_user_created", email="admin@example.com")
    else:
        logger.info("admin_user_already_exists")


async def main():
    from app.db.session import AsyncSessionLocal

    """Run database initialization."""
    async with AsyncSessionLocal() as db:
        await init_db(db)
    print("Database initialized successfully!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
