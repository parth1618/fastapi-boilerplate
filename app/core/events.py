"""Application startup and shutdown events."""

import structlog
from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.db.session import db_manager
from app.utils.logging import setup_logging

logger = structlog.get_logger()


async def on_startup(app: FastAPI) -> None:
    """Execute on application startup."""
    # Setup logging
    setup_logging()

    logger.info(
        "application_starting",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
    )

    # Initialize database manager
    db_manager.init()

    # Test database connection
    if db_manager.engine is None:
        logger.error("database_engine_not_initialized")
        raise RuntimeError("Database engine not initialized")

    try:
        async with db_manager.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_connection_successful")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        raise


async def on_shutdown(app: FastAPI) -> None:
    """Execute on application shutdown."""
    logger.info("application_shutting_down")

    # Dispose database engine
    if db_manager.engine is not None:
        await db_manager.engine.dispose()
        logger.info("database_engine_disposed")
    else:
        logger.warning("database_engine_already_disposed")
