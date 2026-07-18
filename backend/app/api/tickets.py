"""Tickets API — CRUD endpoints for ticket management."""

import uuid
import logging

from fastapi import APIRouter, HTTPException, Query

from app.schemas.ticket import (
    CreateTicketRequest,
    UpdateTicketRequest,
    TicketResponse,
    TicketListResponse,
    TicketEventResponse,
)
from app.services.ticket_service import (
    create_ticket,
    get_ticket,
    list_tickets,
    update_ticket_status,
    add_ticket_comment,
)

logger = logging.getLogger("customer_service.api.tickets")
router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])


@router.get("", response_model=TicketListResponse)
async def list_tickets_endpoint(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    assigned_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List tickets with optional filters."""
    tickets, total = await list_tickets(
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        page=page,
        page_size=page_size,
    )
    return TicketListResponse(
        tickets=[TicketResponse.model_validate(t) for t in tickets],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket_endpoint(req: CreateTicketRequest):
    """Create a new ticket."""
    ticket = await create_ticket(
        title=req.title,
        conversation_id=req.conversation_id,
        customer_id=req.customer_id,
        description=req.description,
        category=req.category,
        priority=req.priority,
    )
    return TicketResponse.model_validate(ticket)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket_endpoint(ticket_id: uuid.UUID):
    """Get ticket details with events."""
    ticket = await get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketResponse.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket_endpoint(ticket_id: uuid.UUID, req: UpdateTicketRequest):
    """Update ticket (status, assignee, etc.)."""
    try:
        ticket = await update_ticket_status(
            ticket_id=ticket_id,
            to_status=req.status,
            triggered_by="api",
            comment=req.comment,
            resolution=req.resolution,
            assigned_to=req.assigned_to,
            assigned_dept=req.assigned_dept,
        )
        return TicketResponse.model_validate(ticket)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{ticket_id}/comments")
async def add_comment_endpoint(ticket_id: uuid.UUID, comment: str):
    """Add a comment to a ticket."""
    await add_ticket_comment(ticket_id, comment, triggered_by="api")
    return {"status": "ok"}
