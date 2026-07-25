"""Contract tests for the Python-to-Java ticket client."""

import asyncio
import json

import httpx

from app.clients.java_ticket_client import JavaTicketClient, TicketServiceError


def test_create_ticket_uses_java_contract() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            201,
            json={
                "ticketId": 10001,
                "status": "NEW",
                "deadline": "2026-07-25T18:00:00+08:00",
            },
        )

    async def run() -> dict:
        client = JavaTicketClient(
            base_url="http://ticket-service:8080",
            transport=httpx.MockTransport(handler),
        )
        try:
            return await client.create_ticket(
                request_id="req-20260725-001",
                conversation_id="conv-1001",
                user_id="user-101",
                category="REFUND",
                priority="HIGH",
                summary="用户申请订单退款",
            )
        finally:
            await client.close()

    response = asyncio.run(run())
    assert response["ticketId"] == 10001
    assert captured == {
        "path": "/api/tickets",
        "body": {
            "requestId": "req-20260725-001",
            "conversationId": "conv-1001",
            "userId": "user-101",
            "category": "REFUND",
            "priority": "HIGH",
            "summary": "用户申请订单退款",
        },
    }


def test_java_error_is_exposed_as_stable_client_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "code": "INVALID_STATUS_TRANSITION",
                "message": "Invalid ticket status transition: ASSIGNED -> CLOSED",
            },
        )

    async def run() -> None:
        client = JavaTicketClient(
            base_url="http://ticket-service:8080",
            transport=httpx.MockTransport(handler),
        )
        try:
            await client.change_status(
                10001,
                status="CLOSED",
                operator_id="agent-1",
            )
        finally:
            await client.close()

    try:
        asyncio.run(run())
    except TicketServiceError as exc:
        assert exc.status_code == 422
        assert "ASSIGNED -> CLOSED" in str(exc)
    else:
        raise AssertionError("TicketServiceError was not raised")
