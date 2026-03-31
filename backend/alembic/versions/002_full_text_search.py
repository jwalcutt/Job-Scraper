"""Add full-text search index to jobs

Revision ID: 002
Revises: 001
Create Date: 2026-03-26
"""
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

# Expression used for the GIN index — must match what search queries use exactly
_FTS_EXPR = (
    "to_tsvector('english', "
    "coalesce(title,'') || ' ' || coalesce(company,'') || ' ' || coalesce(description,''))"
)


def upgrade() -> None:
    # Functional GIN index — no extra column needed; PostgreSQL uses it automatically
    # when the query WHERE clause matches this exact expression.
    op.execute(f"CREATE INDEX ix_jobs_fts ON jobs USING GIN({_FTS_EXPR})")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_jobs_fts")
