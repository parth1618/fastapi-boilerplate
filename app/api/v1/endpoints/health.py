"""Health check endpoints."""

import redis.asyncio as aioredis
from fastapi import APIRouter, status
from sqlalchemy import text

from app.core.config import settings
from app.dependencies.db import DBSession
from app.schemas.message import HealthCheck

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheck, status_code=status.HTTP_200_OK)
async def health_check(db: DBSession) -> HealthCheck:
    """Health check endpoint with database and Redis status."""
    # Check database
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    # Check Redis
    redis_status = "healthy"
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        await redis_client.close()
    except Exception:
        redis_status = "unhealthy"

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
