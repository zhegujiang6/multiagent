"""Chat-related Pydantic request/response schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    customer_id: str = Field(default="anonymous", max_length=255)
    channel: str = Field(default="web", max_length=50)
    customer_name: str | None = None
    customer_email: str | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    customer_id: str
    channel: str
    status: str
    sentiment_trend: list = []
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    content_type: str = Field(default="text", max_length=30)


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    content_type: str
    meta_info: dict = Field(default={}, serialization_alias="metadata")
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentStatusMessage(BaseModel):
    """WebSocket message: agent processing status update."""
    type: str = "agent_status"
    agent: str
    status: str  # "started", "completed", "error"
    message: str | None = None


class ChatResponse(BaseModel):
    """Full chat response after message processing."""
    conversation_id: uuid.UUID
    message: MessageResponse
    agent_statuses: list[AgentStatusMessage] = []
    ticket_created: dict | None = None
    escalated: bool = False
