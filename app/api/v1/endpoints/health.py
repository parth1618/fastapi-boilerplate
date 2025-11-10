"""Health check endpoints."""

import asyncio

import redis.asyncio as aioredis
from fastapi import APIRouter, status
from sqlalchemy import text

from app.core.config import settings
from app.dependencies.db import DBSession
from app.schemas.message import HealthCheck

router = APIRouter(tags=["Health"])


async def check_database_health(db: DBSession, timeout: float = 2.0) -> str:
    """Check database health with timeout."""
    try:
        async with asyncio.timeout(timeout):
            await db.execute(text("SELECT 1"))
        return "healthy"
    except TimeoutError:
        return "timeout"
    except Exception:
        return "unhealthy"


async def check_redis_health(timeout: float = 2.0) -> str:
    """Check Redis health with timeout."""
    try:
        async with asyncio.timeout(timeout):
            redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await redis_client.ping()
            await redis_client.close()
        return "healthy"
    except TimeoutError:
        return "timeout"
    except Exception:
        return "unhealthy"


@router.get("/health", response_model=HealthCheck, status_code=status.HTTP_200_OK)
async def health_check(db: DBSession) -> HealthCheck:
    """Health check endpoint with database and Redis status."""
    # Check database with timeout
    db_status = await check_database_health(db, timeout=2.0)

    # Check Redis with timeout
    redis_status = await check_redis_health(timeout=2.0)

    overall_status = (
        "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy"
    )

    return HealthCheck(
        status=overall_status,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
        redis=redis_status,
    )


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> dict[str, str]:
    """Readiness check endpoint."""
    return {"status": "ready"}
