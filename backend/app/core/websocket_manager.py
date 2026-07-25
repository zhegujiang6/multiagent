"""Connection registry used by chat and asynchronous ticket events."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._send_locks: dict[int, asyncio.Lock] = {}
        self._lock = asyncio.Lock()

    async def connect(self, conversation_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[conversation_id].add(websocket)
            self._send_locks[id(websocket)] = asyncio.Lock()

    async def disconnect(self, conversation_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(conversation_id)
            if connections is None:
                return
            connections.discard(websocket)
            self._send_locks.pop(id(websocket), None)
            if not connections:
                self._connections.pop(conversation_id, None)

    async def publish_ticket_event(self, event: dict[str, Any]) -> None:
        conversation_id = str(event.get("conversationId") or "")
        async with self._lock:
            if conversation_id:
                targets = list(
                    self._connections.get(conversation_id, set())
                    | self._connections.get("", set())
                )
            else:
                targets = [
                    connection
                    for connections in self._connections.values()
                    for connection in connections
                ]

        message_type = {
            "ticket.created": "ticket_created",
            "ticket.status.changed": "ticket_updated",
            "ticket.sla.overdue": "ticket_sla_overdue",
        }.get(event.get("eventType"), "ticket_event")
        message = {"type": message_type, "ticket": event}

        stale: list[WebSocket] = []
        for websocket in targets:
            try:
                await self.send_json(websocket, message)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            await self.disconnect(conversation_id, websocket)

    async def send_json(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        lock = self._send_locks.get(id(websocket))
        if lock is None:
            await websocket.send_json(message)
            return
        async with lock:
            await websocket.send_json(message)


websocket_manager = WebSocketManager()
