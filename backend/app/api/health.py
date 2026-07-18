"""Health check endpoint."""

from fastapi import APIRouter

from sqlalchemy import text

from app.core.database import async_session_factory
from app.core.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
async def health_check():
    """Comprehensive health check for all dependencies."""
    checks = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "qdrant": "unknown",
    }

    # Check PostgreSQL
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"
        checks["status"] = "degraded"

    # Check Redis
    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {e}"
        checks["status"] = "degraded"

    # Check Qdrant
    try:
        from app.rag.vector_store import get_client
        client = get_client()
        client.get_collections()
        checks["qdrant"] = "healthy"
    except Exception as e:
        checks["qdrant"] = f"unhealthy: {e}"
        checks["status"] = "degraded"

    return checks
