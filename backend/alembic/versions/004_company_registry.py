"""Company registry table for career page crawling

Revision ID: 004
Revises: 003
Create Date: 2026-03-26
"""
import sqlalchemy as sa

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("careers_url", sa.Text(), nullable=False, unique=True),
        sa.Column("ats_type", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_companies_name", "companies", ["name"])
    op.create_index("ix_companies_ats_type", "companies", ["ats_type"])


def downgrade() -> None:
    op.drop_index("ix_companies_ats_type", "companies")
    op.drop_index("ix_companies_name", "companies")
    op.drop_table("companies")
