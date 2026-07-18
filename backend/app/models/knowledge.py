"""Knowledge Article ORM model."""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Float, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    source_ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id")
    )
    source_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), default="draft")
    meta_info: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    canonical_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(30), default="manual", nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    owner: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    effectiveness_score: Mapped[float] = mapped_column(Float, default=0.0)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions = relationship(
        "KnowledgeArticleVersion",
        back_populates="article",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class KnowledgeArticleVersion(Base):
    __tablename__ = "knowledge_article_versions"
    __table_args__ = (
        UniqueConstraint("article_id", "version_number", name="uq_knowledge_version_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    change_summary: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    article = relationship("KnowledgeArticle", back_populates="versions")
    chunks = relationship(
        "KnowledgeChunk",
        back_populates="version",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("version_id", "chunk_index", name="uq_knowledge_chunk_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_article_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    vector_point_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meta_info: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    version = relationship("KnowledgeArticleVersion", back_populates="chunks")


class RetrievalEvent(Base):
    __tablename__ = "retrieval_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    rewritten_query: Mapped[str | None] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(100))
    result_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    result_scores: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    selected_article_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    answered: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class KnowledgeFeedback(Base):
    __tablename__ = "knowledge_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retrieval_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retrieval_events.id", ondelete="SET NULL"), index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), index=True
    )
    article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_articles.id", ondelete="SET NULL"), index=True
    )
    feedback_type: Mapped[str] = mapped_column(String(30), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    comment: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(30), default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
