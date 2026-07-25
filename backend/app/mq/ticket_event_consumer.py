"""RocketMQ consumer that relays Java ticket events to FastAPI WebSockets."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.core.config import settings
from app.core.websocket_manager import websocket_manager

logger = logging.getLogger("customer_service.mq.ticket")


class TicketEventConsumer:
    def __init__(self) -> None:
        self._consumer: Any = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        if not settings.rocketmq_consumer_enabled:
            logger.info("RocketMQ ticket consumer is disabled")
            return

        try:
            from rocketmq.client import ConsumeStatus, PushConsumer
        except (ImportError, OSError) as exc:
            raise RuntimeError(
                "RocketMQ consumer is enabled but rocketmq-client-python/librocketmq "
                "is not installed"
            ) from exc

        self._loop = asyncio.get_running_loop()
        consumer = PushConsumer(settings.rocketmq_consumer_group)
        consumer.set_name_server_address(settings.rocketmq_name_server)

        def callback(message: Any) -> Any:
            try:
                body = message.body
                if isinstance(body, bytes):
                    body = body.decode("utf-8")
                event = json.loads(body)
                if self._loop is not None:
                    asyncio.run_coroutine_threadsafe(
                        self._handle_event(event),
                        self._loop,
                    )
                return ConsumeStatus.CONSUME_SUCCESS
            except Exception:
                logger.exception("Failed to process ticket event")
                return ConsumeStatus.RECONSUME_LATER

        consumer.subscribe("ticket-events", callback)
        consumer.start()
        self._consumer = consumer
        logger.info("RocketMQ ticket consumer started")

    async def stop(self) -> None:
        if self._consumer is not None:
            self._consumer.shutdown()
            self._consumer = None

    async def _handle_event(self, event: dict[str, Any]) -> None:
        await websocket_manager.publish_ticket_event(event)

        if (
            event.get("eventType") == "ticket.status.changed"
            and event.get("toStatus") == "RESOLVED"
            and event.get("conversationId")
        ):
            from app.services.knowledge_lifecycle_service import (
                auto_extract_knowledge,
            )

            asyncio.create_task(
                auto_extract_knowledge(
                    ticket_id=str(event.get("ticketId")),
                    conversation_id=str(event["conversationId"]),
                )
            )


ticket_event_consumer = TicketEventConsumer()
