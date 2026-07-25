"""Ticket BFF routes.

The Python service never reads or writes the ticket tables. It forwards all
ticket commands and queries to the Java business service and only adapts the
response shape expected by the existing React application.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.clients.java_ticket_client import (
    TicketServiceError,
    get_java_ticket_client,
)
from app.schemas.ticket import (
    AssignTicketRequest,
    CreateTicketRequest,
    UpdateTicketRequest,
)

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])

STATUS_TO_JAVA = {
    "new": "NEW",
    "assigned": "ASSIGNED",
    "in_progress": "IN_PROGRESS",
    "pending": "PENDING",
    "resolved": "RESOLVED",
    "closed": "CLOSED",
    "reopened": "REOPENED",
}
PRIORITY_TO_JAVA = {
    "p0": "URGENT",
    "p1": "HIGH",
    "p2": "MEDIUM",
    "p3": "LOW",
    "critical": "URGENT",
    "urgent": "URGENT",
    "high": "HIGH",
    "medium": "MEDIUM",
    "low": "LOW",
}
PRIORITY_FROM_JAVA = {
    "URGENT": "critical",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
}


def _service_error(exc: TicketServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


def _java_status(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    return STATUS_TO_JAVA.get(normalized, value.upper())


def _java_priority(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    return PRIORITY_TO_JAVA.get(normalized, value.upper())


def _legacy_ticket(ticket: dict[str, Any]) -> dict[str, Any]:
    ticket_id = ticket.get("ticketId")
    status = str(ticket.get("status") or "NEW").lower()
    priority = PRIORITY_FROM_JAVA.get(
        str(ticket.get("priority") or "MEDIUM").upper(),
        "medium",
    )
    logs = [
        {
            "id": str(log.get("id")),
            "from_status": (
                str(log["fromStatus"]).lower()
                if log.get("fromStatus")
                else None
            ),
            "to_status": str(log.get("toStatus") or "").lower(),
            "triggered_by": log.get("operatorId") or "system",
            "comment": log.get("reason"),
            "created_at": log.get("createdAt"),
        }
        for log in ticket.get("statusLogs") or []
    ]
    return {
        "id": str(ticket_id),
        "ticket_id": ticket_id,
        "display_id": f"TK-{int(ticket_id):08d}" if ticket_id is not None else "",
        "request_id": ticket.get("requestId"),
        "conversation_id": ticket.get("conversationId"),
        "customer_id": ticket.get("userId"),
        "user_id": ticket.get("userId"),
        "title": ticket.get("summary") or "",
        "summary": ticket.get("summary") or "",
        "description": ticket.get("summary") or "",
        "category": str(ticket.get("category") or "").lower(),
        "priority": priority,
        "status": status,
        "assigned_to": ticket.get("assigneeId"),
        "assignee_id": ticket.get("assigneeId"),
        "sla_deadline": ticket.get("deadline"),
        "deadline": ticket.get("deadline"),
        "version": ticket.get("version"),
        "resolution": None,
        "created_at": ticket.get("createdAt"),
        "updated_at": ticket.get("updatedAt"),
        "events": logs,
    }


@router.get("")
async def list_tickets_endpoint(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    assigned_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        result = await get_java_ticket_client().list_tickets(
            status=_java_status(status),
            priority=_java_priority(priority),
            assignee_id=assigned_to,
            page=page,
            page_size=page_size,
        )
    except TicketServiceError as exc:
        raise _service_error(exc) from exc
    return {
        "tickets": [_legacy_ticket(ticket) for ticket in result.get("tickets", [])],
        "total": result.get("total", 0),
        "page": result.get("page", page),
        "page_size": result.get("pageSize", page_size),
    }


@router.post("", status_code=201)
async def create_ticket_endpoint(req: CreateTicketRequest):
    summary = req.summary or req.description or req.title
    if not summary:
        raise HTTPException(status_code=422, detail="summary is required")
    user_id = req.user_id or req.customer_id
    if not user_id:
        raise HTTPException(status_code=422, detail="user_id is required")
    try:
        return await get_java_ticket_client().create_ticket(
            request_id=req.request_id or f"api-{uuid.uuid4()}",
            conversation_id=req.conversation_id,
            user_id=user_id,
            category=req.category.upper(),
            priority=_java_priority(req.priority) or "MEDIUM",
            summary=summary,
        )
    except TicketServiceError as exc:
        raise _service_error(exc) from exc


@router.get("/{ticket_id}")
async def get_ticket_endpoint(ticket_id: int):
    try:
        ticket = await get_java_ticket_client().get_ticket(ticket_id)
    except TicketServiceError as exc:
        raise _service_error(exc) from exc
    return _legacy_ticket(ticket)


@router.patch("/{ticket_id}")
async def update_ticket_endpoint(ticket_id: int, req: UpdateTicketRequest):
    client = get_java_ticket_client()
    try:
        result: dict[str, Any] | None = None
        if req.assigned_to:
            result = await client.assign_ticket(
                ticket_id,
                assignee_id=req.assigned_to,
                operator_id=req.operator_id,
                reason=req.comment,
            )
        if req.status:
            result = await client.change_status(
                ticket_id,
                status=_java_status(req.status) or req.status.upper(),
                operator_id=req.operator_id,
                reason=req.comment,
            )
        if result is None:
            raise HTTPException(
                status_code=422,
                detail="status or assigned_to is required",
            )
    except TicketServiceError as exc:
        raise _service_error(exc) from exc
    return _legacy_ticket(result)


@router.post("/{ticket_id}/assign")
async def assign_ticket_endpoint(ticket_id: int, req: AssignTicketRequest):
    try:
        ticket = await get_java_ticket_client().assign_ticket(
            ticket_id,
            assignee_id=req.assignee_id,
            operator_id=req.operator_id,
            reason=req.reason,
        )
    except TicketServiceError as exc:
        raise _service_error(exc) from exc
    return _legacy_ticket(ticket)
