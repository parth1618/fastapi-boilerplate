"""Enhanced database session management with connection pooling."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from sqlalchemy import event, exc, pool, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings

logger = structlog.get_logger()


class DatabaseSessionManager:
    """Manage database connections with advanced pooling and health checks."""

    def __init__(self) -> None:
        """Initialize database session manager."""
        self._initialized = False
        self.engine: AsyncEngine | None = None
        self.sessionmaker: async_sessionmaker[AsyncSession] | None = None

    def init(self) -> None:
        """Initialize database engine with connection pooling."""
        if self._initialized:
            return

        # Determine pool class based on environment
        pool_class: type[pool.Pool] | type[NullPool]
        pool_class = NullPool if settings.ENVIRONMENT == "testing" else QueuePool

        # Create async engine with advanced configuration
        self.engine = create_async_engine(
            str(settings.DATABASE_URL),
            echo=settings.DB_ECHO,
            # Pool configuration
            poolclass=pool_class,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=30.0,  # Seconds to wait for connection from pool
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Verify connections before using
            # Connection arguments
            connect_args={
                "server_settings": {
                    "application_name": settings.PROJECT_NAME,
                    "jit": "off",  # Disable JIT for better connection pool performance
                },
                "command_timeout": 60,  # Command timeout in seconds
                "timeout": 10,  # Connection timeout in seconds
            },
            # Execution options
            execution_options={
                "isolation_level": "READ COMMITTED",
            },
        )

        # Set up event listeners for connection pool monitoring
        self._setup_event_listeners()

        # Create session factory
        self.sessionmaker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        self._initialized = True
        logger.info(
            "database_engine_initialized",
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
        )

    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners for monitoring."""
        if not self.engine:
            return

        @event.listens_for(self.engine.sync_engine, "connect")
        def receive_connect(dbapi_conn: Any, connection_record: Any) -> None:
            """Log new database connections."""
            logger.debug("database_connection_opened")

        @event.listens_for(self.engine.sync_engine, "close")
        def receive_close(dbapi_conn: Any, connection_record: Any) -> None:
            """Log closed database connections."""
            logger.debug("database_connection_closed")

        @event.listens_for(self.engine.sync_engine, "checkout")
        def receive_checkout(
            dbapi_conn: Any,
            connection_record: Any,
            connection_proxy: Any,
        ) -> None:
            """Log connection checkout from pool."""
            logger.debug("database_connection_checkout")

        @event.listens_for(self.engine.sync_engine, "checkin")
        def receive_checkin(dbapi_conn: Any, connection_record: Any) -> None:
            """Log connection checkin to pool."""
            logger.debug("database_connection_checkin")

    async def close(self) -> None:
        """Close database engine and all connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("database_engine_disposed")
            self._initialized = False

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional scope for database operations.

        Yields:
            AsyncSession: Database session

        Raises:
            Exception: If session creation or transaction fails
        """
        if not self._initialized:
            self.init()

        if not self.sessionmaker:
            raise RuntimeError("Database sessionmaker not initialized")

        session = self.sessionmaker()
        try:
            yield session
            await session.commit()
        except exc.SQLAlchemyError as e:
            await session.rollback()
            logger.error(
                "database_transaction_rollback",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        except Exception as e:
            await session.rollback()
            logger.error(
                "database_transaction_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        finally:
            await session.close()

    async def health_check(self) -> dict[str, Any]:
        """Check database connection health.

        Returns:
            dict: Health check results
        """
        if not self.engine:
            return {
                "status": "unhealthy",
                "error": "Engine not initialized",
            }

        try:
            # Test connection - use text() to create proper SQL statement
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

            # Get pool statistics
            pool_status = (
                self.engine.pool.status() if hasattr(self.engine.pool, "status") else "N/A"
            )

            return {
                "status": "healthy",
                "pool_status": pool_status,
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
            }
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# Global database session manager instance
db_manager = DatabaseSessionManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session.

    Yields:
        AsyncSession: Database session
    """
    async with db_manager.session() as session:
        yield session


async def init_db() -> None:
    """Initialize database engine on application startup."""
    db_manager.init()

    # Verify connection
    health = await db_manager.health_check()
    if health["status"] != "healthy":
        raise RuntimeError(f"Database initialization failed: {health.get('error')}")

    logger.info("database_initialized", health=health)


async def close_db() -> None:
    """Close database engine on application shutdown."""
    await db_manager.close()


# Connection pool monitoring utilities
async def get_pool_status() -> dict[str, Any]:
    """Get current connection pool status.

    Returns:
        dict: Pool statistics
    """
    if not db_manager.engine:
        return {"error": "Engine not initialized"}

    pool_obj = db_manager.engine.pool

    return {
        "size": pool_obj.size() if hasattr(pool_obj, "size") else "N/A",
        "checked_in": pool_obj.checkedin() if hasattr(pool_obj, "checkedin") else "N/A",
        "checked_out": pool_obj.checkedout() if hasattr(pool_obj, "checkedout") else "N/A",
        "overflow": pool_obj.overflow() if hasattr(pool_obj, "overflow") else "N/A",
        "total": pool_obj.size() + pool_obj.overflow()
        if hasattr(pool_obj, "size") and hasattr(pool_obj, "overflow")
        else "N/A",
    }


async def test_connection_with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
) -> bool:
    """Test database connection with retry logic.

    Args:
        max_attempts: Maximum number of connection attempts
        delay: Delay between attempts in seconds

    Returns:
        bool: True if connection successful, False otherwise
    """
    for attempt in range(1, max_attempts + 1):
        try:
            health = await db_manager.health_check()
            if health["status"] == "healthy":
                logger.info(
                    "database_connection_successful",
                    attempt=attempt,
                )
                return True
        except Exception as e:
            logger.warning(
                "database_connection_attempt_failed",
                attempt=attempt,
                max_attempts=max_attempts,
                error=str(e),
            )

            if attempt < max_attempts:
                await asyncio.sleep(delay)

    logger.error("database_connection_failed", max_attempts=max_attempts)
    return False
