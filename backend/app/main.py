"""FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.redis import get_redis, close_redis
from app.middleware.logging import LoggingMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

logger = logging.getLogger("customer_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Customer Service Agent...")
    await get_redis()

    # Start SLA polling as background task
    sla_task = asyncio.create_task(_sla_polling())

    yield

    # Shutdown
    logger.info("Shutting down...")
    sla_task.cancel()
    try:
        await sla_task
    except asyncio.CancelledError:
        pass
    await close_redis()


async def _sla_polling():
    """Background SLA polling loop."""
    try:
        from app.services.sla_service import sla_polling_loop
        await sla_polling_loop()
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"SLA polling failed to start: {e}")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit logging
app.add_middleware(LoggingMiddleware)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"service": settings.app_name, "version": "0.1.0", "status": "running"}
