"""Add compact conversation state and cross-conversation customer memory.

Revision ID: c5e8d4f1a9b2
Revises: f4a9c2e71d30
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c5e8d4f1a9b2"
down_revision = "f4a9c2e71d30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_memories",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("conversation_id", sa.UUID(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("completed_actions", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("pending_items", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("intent", sa.String(length=100), nullable=True),
        sa.Column("sentiment", sa.String(length=30), nullable=True),
        sa.Column("satisfaction", sa.String(length=30), nullable=False, server_default="unknown"),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("turn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_compressed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_conversation_memories_conversation_id", "conversation_memories", ["conversation_id"])

    op.create_table(
        "user_memories",
        sa.Column("customer_id", sa.String(length=255), primary_key=True),
        sa.Column("conversation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resolved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("escalation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latest_sentiment", sa.String(length=30), nullable=True),
        sa.Column("satisfaction", sa.String(length=30), nullable=False, server_default="unknown"),
        sa.Column("satisfaction_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("preferences", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("open_tasks", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("last_session_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("user_memories")
    op.drop_index("ix_conversation_memories_conversation_id", table_name="conversation_memories")
    op.drop_table("conversation_memories")
