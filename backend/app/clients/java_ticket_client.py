"""Async client for the Java ticket business service."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("customer_service.clients.ticket")


class TicketServiceError(RuntimeError):
    """A stable application error for failed Java ticket-service calls."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


class JavaTicketClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._client = httpx.AsyncClient(
            base_url=(base_url or settings.ticket_service_url).rstrip("/"),
            timeout=timeout or settings.ticket_service_timeout_seconds,
            transport=transport,
        )

    async def create_ticket(
        self,
        *,
        request_id: str,
        conversation_id: str,
        user_id: str,
        category: str,
        priority: str,
        summary: str,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/tickets",
            json={
                "requestId": request_id,
                "conversationId": conversation_id,
                "userId": user_id,
                "category": category,
                "priority": priority,
                "summary": summary,
            },
        )

    async def get_ticket(self, ticket_id: str | int) -> dict[str, Any]:
        return await self._request("GET", f"/api/tickets/{ticket_id}")

    async def list_tickets(
        self,
        *,
        status: str | None = None,
        priority: str | None = None,
        assignee_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if status:
            params["status"] = status
        if priority:
            params["priority"] = priority
        if assignee_id:
            params["assigneeId"] = assignee_id
        return await self._request("GET", "/api/tickets", params=params)

    async def change_status(
        self,
        ticket_id: str | int,
        *,
        status: str,
        operator_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/tickets/{ticket_id}/status",
            json={
                "status": status,
                "operatorId": operator_id,
                "reason": reason,
            },
        )

    async def assign_ticket(
        self,
        ticket_id: str | int,
        *,
        assignee_id: str,
        operator_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/tickets/{ticket_id}/assign",
            json={
                "assigneeId": assignee_id,
                "operatorId": operator_id,
                "reason": reason,
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            logger.error("Ticket service unavailable: %s", exc)
            raise TicketServiceError("Ticket service is unavailable") from exc

        if response.is_error:
            try:
                error_body = response.json()
                detail = error_body.get("message") or error_body.get("detail")
            except ValueError:
                detail = response.text
            raise TicketServiceError(
                detail or f"Ticket service returned HTTP {response.status_code}",
                status_code=response.status_code,
            )

        return response.json()


_ticket_client: JavaTicketClient | None = None


def get_java_ticket_client() -> JavaTicketClient:
    global _ticket_client
    if _ticket_client is None:
        _ticket_client = JavaTicketClient()
    return _ticket_client


async def close_java_ticket_client() -> None:
    global _ticket_client
    if _ticket_client is not None:
        await _ticket_client.close()
        _ticket_client = None
