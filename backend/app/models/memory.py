"""Persistent memory models for conversation continuity and customer context."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConversationMemory(Base):
    """A compact, task-oriented memory for one conversation."""

    __tablename__ = "conversation_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    goal: Mapped[str | None] = mapped_column(Text)
    completed_actions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    pending_items: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    next_action: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    intent: Mapped[str | None] = mapped_column(String(100))
    sentiment: Mapped[str | None] = mapped_column(String(30))
    satisfaction: Mapped[str] = mapped_column(String(30), default="unknown", nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_compressed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UserMemory(Base):
    """Cross-conversation memory containing only stable customer-service facts."""

    __tablename__ = "user_memories"

    customer_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    conversation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resolved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    escalation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latest_sentiment: Mapped[str | None] = mapped_column(String(30))
    satisfaction: Mapped[str] = mapped_column(String(30), default="unknown", nullable=False)
    satisfaction_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    preferences: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    open_tasks: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    last_session_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
