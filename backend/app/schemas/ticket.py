"""Schemas accepted by the Python BFF before forwarding to Java."""

from pydantic import BaseModel, Field


class CreateTicketRequest(BaseModel):
    request_id: str | None = None
    conversation_id: str
    user_id: str | None = None
    customer_id: str | None = None
    category: str
    priority: str = "medium"
    summary: str | None = None
    title: str | None = None
    description: str | None = None


class UpdateTicketRequest(BaseModel):
    status: str | None = None
    assigned_to: str | None = None
    operator_id: str = Field(default="api", min_length=1, max_length=100)
    comment: str | None = Field(default=None, max_length=1000)


class AssignTicketRequest(BaseModel):
    assignee_id: str = Field(min_length=1, max_length=100)
    operator_id: str = Field(default="api", min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=1000)
