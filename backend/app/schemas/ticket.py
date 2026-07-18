"""Ticket-related Pydantic request/response schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class CreateTicketRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    category: str | None = None
    priority: str = Field(default="P3", pattern=r"^P[0-3]$")


class UpdateTicketRequest(BaseModel):
    status: str | None = None
    assigned_to: str | None = None
    assigned_dept: str | None = None
    priority: str | None = None
    resolution: str | None = None
    comment: str | None = None


class TicketEventResponse(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    from_status: str | None
    to_status: str
    triggered_by: str
    comment: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketResponse(BaseModel):
    id: uuid.UUID
    display_id: str
    conversation_id: uuid.UUID | None
    customer_id: uuid.UUID | None
    title: str
    description: str | None
    category: str | None
    priority: str
    status: str
    assigned_to: str | None
    assigned_dept: str | None
    sla_deadline: datetime | None
    sla_response_deadline: datetime | None
    sla_warning_sent: bool = False
    sla_escalated: bool = False
    resolution: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None
    events: list[TicketEventResponse] = []

    model_config = {"from_attributes": True}


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]
    total: int
    page: int = 1
    page_size: int = 20
