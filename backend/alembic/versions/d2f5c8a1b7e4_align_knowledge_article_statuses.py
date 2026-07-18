"""Align knowledge article statuses with the application workflow.

Revision ID: d2f5c8a1b7e4
Revises: 69e6c7beed04
Create Date: 2026-07-17
"""

from alembic import op


revision = "d2f5c8a1b7e4"
down_revision = "69e6c7beed04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "knowledge_articles_status_check",
        "knowledge_articles",
        type_="check",
    )
    op.create_check_constraint(
        "knowledge_articles_status_check",
        "knowledge_articles",
        "status IN ('draft', 'review', 'published', 'deprecated', 'approved', 'rejected', 'gap')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "knowledge_articles_status_check",
        "knowledge_articles",
        type_="check",
    )
    op.create_check_constraint(
        "knowledge_articles_status_check",
        "knowledge_articles",
        "status IN ('draft', 'review', 'published', 'deprecated')",
    )
