"""Ticket and TicketEvent ORM models."""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Float, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    display_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id")
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    priority: Mapped[str] = mapped_column(String(10), default="P3")
    status: Mapped[str] = mapped_column(String(30), default="new")
    assigned_to: Mapped[str | None] = mapped_column(String(255))
    assigned_dept: Mapped[str | None] = mapped_column(String(100))
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_response_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_warning_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sla_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution: Mapped[str | None] = mapped_column(Text)
    parent_ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id")
    )
    meta_info: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversation = relationship("Conversation", back_populates="tickets")
    events = relationship("TicketEvent", back_populates="ticket", lazy="selectin")


class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ticket = relationship("Ticket", back_populates="events")
