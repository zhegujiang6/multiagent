"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.redis import get_redis, close_redis
from app.middleware.logging import LoggingMiddleware
from app.clients.java_ticket_client import close_java_ticket_client
from app.mq.ticket_event_consumer import ticket_event_consumer

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

    # Ticket lifecycle and SLA checks live in Java. Python only consumes events.
    await ticket_event_consumer.start()

    yield

    # Shutdown
    logger.info("Shutting down...")
    await ticket_event_consumer.stop()
    await close_java_ticket_client()
    await close_redis()


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
