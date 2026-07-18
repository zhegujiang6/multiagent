"""Add knowledge data platform assets, lineage, retrieval and feedback.

Revision ID: f4a9c2e71d30
Revises: d2f5c8a1b7e4
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f4a9c2e71d30"
down_revision = "d2f5c8a1b7e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("knowledge_articles", sa.Column("canonical_key", sa.String(255), nullable=True))
    op.add_column("knowledge_articles", sa.Column("content_hash", sa.String(64), nullable=True))
    op.add_column("knowledge_articles", sa.Column("source_type", sa.String(30), nullable=False, server_default="manual"))
    op.add_column("knowledge_articles", sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("knowledge_articles", sa.Column("owner", sa.String(100), nullable=False, server_default="system"))
    op.add_column("knowledge_articles", sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"))
    op.add_column("knowledge_articles", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("knowledge_articles", sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE knowledge_articles SET canonical_key = 'legacy:' || id::text WHERE canonical_key IS NULL")
    op.execute("UPDATE knowledge_articles SET content_hash = md5(coalesce(title, '') || E'\\n' || coalesce(content, '')) WHERE content_hash IS NULL")
    op.execute("""
        UPDATE knowledge_articles
        SET status = 'rejected',
            metadata = coalesce(metadata, '{}'::jsonb) || '{"quarantine_reason":"malformed message serialization"}'::jsonb
        WHERE status = 'gap'
          AND title LIKE 'content=%'
          AND title LIKE '%additional_kwargs=%'
    """)

    op.alter_column("knowledge_articles", "canonical_key", nullable=False)
    op.alter_column("knowledge_articles", "content_hash", nullable=False)
    op.create_index("uq_knowledge_articles_canonical_key", "knowledge_articles", ["canonical_key"], unique=True)
    op.create_index("ix_knowledge_articles_content_hash", "knowledge_articles", ["content_hash"])

    op.create_table(
        "knowledge_article_versions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("article_id", sa.UUID(), sa.ForeignKey("knowledge_articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("change_summary", sa.String(500), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(100), nullable=False, server_default="system"),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("article_id", "version_number", name="uq_knowledge_version_number"),
    )
    op.create_index("ix_knowledge_article_versions_article_id", "knowledge_article_versions", ["article_id"])
    op.create_index("ix_knowledge_article_versions_content_hash", "knowledge_article_versions", ["content_hash"])

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("version_id", sa.UUID(), sa.ForeignKey("knowledge_article_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("article_id", sa.UUID(), sa.ForeignKey("knowledge_articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("vector_point_id", sa.String(64), nullable=True, unique=True),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("version_id", "chunk_index", name="uq_knowledge_chunk_index"),
    )
    op.create_index("ix_knowledge_chunks_version_id", "knowledge_chunks", ["version_id"])
    op.create_index("ix_knowledge_chunks_article_id", "knowledge_chunks", ["article_id"])
    op.create_index("ix_knowledge_chunks_content_hash", "knowledge_chunks", ["content_hash"])

    op.create_table(
        "retrieval_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("conversation_id", sa.UUID(), sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("rewritten_query", sa.Text(), nullable=True),
        sa.Column("intent", sa.String(100), nullable=True),
        sa.Column("result_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("result_scores", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("selected_article_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("answered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_retrieval_events_conversation_id", "retrieval_events", ["conversation_id"])
    op.create_index("ix_retrieval_events_created_at", "retrieval_events", ["created_at"])

    op.create_table(
        "knowledge_feedback",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("retrieval_event_id", sa.UUID(), sa.ForeignKey("retrieval_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("conversation_id", sa.UUID(), sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("article_id", sa.UUID(), sa.ForeignKey("knowledge_articles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("feedback_type", sa.String(30), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("source", sa.String(30), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_feedback_retrieval_event_id", "knowledge_feedback", ["retrieval_event_id"])
    op.create_index("ix_knowledge_feedback_conversation_id", "knowledge_feedback", ["conversation_id"])
    op.create_index("ix_knowledge_feedback_article_id", "knowledge_feedback", ["article_id"])
    op.create_index("ix_knowledge_feedback_created_at", "knowledge_feedback", ["created_at"])

    op.execute("""
        INSERT INTO knowledge_article_versions
            (id, article_id, version_number, title, content, content_hash, change_summary, status, created_by, approved_by, created_at, published_at)
        SELECT gen_random_uuid(), id, 1, title, content, content_hash, 'Migrated current snapshot', status,
               'migration', CASE WHEN status = 'approved' THEN 'migration' ELSE NULL END,
               created_at, CASE WHEN status = 'approved' THEN updated_at ELSE NULL END
        FROM knowledge_articles
    """)


def downgrade() -> None:
    op.drop_table("knowledge_feedback")
    op.drop_table("retrieval_events")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_article_versions")
    op.drop_index("ix_knowledge_articles_content_hash", table_name="knowledge_articles")
    op.drop_index("uq_knowledge_articles_canonical_key", table_name="knowledge_articles")
    for column in (
        "retired_at", "published_at", "quality_score", "owner", "current_version",
        "source_type", "content_hash", "canonical_key",
    ):
        op.drop_column("knowledge_articles", column)
