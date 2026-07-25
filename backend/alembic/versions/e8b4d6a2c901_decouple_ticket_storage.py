"""Decouple Python knowledge metadata from Java-owned ticket storage.

Revision ID: e8b4d6a2c901
Revises: c5e8d4f1a9b2
Create Date: 2026-07-25
"""

from alembic import op


revision = "e8b4d6a2c901"
down_revision = "c5e8d4f1a9b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE knowledge_articles "
        "DROP CONSTRAINT IF EXISTS knowledge_articles_source_ticket_id_fkey"
    )
    op.execute(
        "ALTER TABLE knowledge_articles "
        "ALTER COLUMN source_ticket_id TYPE VARCHAR(64) "
        "USING source_ticket_id::text"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE knowledge_articles "
        "ALTER COLUMN source_ticket_id TYPE UUID "
        "USING CASE "
        "WHEN source_ticket_id ~* "
        "'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' "
        "THEN source_ticket_id::uuid ELSE NULL END"
    )
