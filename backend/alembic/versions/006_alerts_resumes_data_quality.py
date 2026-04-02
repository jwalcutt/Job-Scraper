"""Job alerts, resume versioning, and data quality columns

Revision ID: 006
Revises: 005
Create Date: 2026-04-01
"""
import sqlalchemy as sa

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Job Alerts (Phase 8.3) ──────────────────────────────────────────────
    op.create_table(
        "job_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("remote", sa.Boolean(), nullable=True),
        sa.Column("min_score", sa.Float(), nullable=False, server_default="0.6"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_alerted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_job_alerts_user_id", "job_alerts", ["user_id"])

    # ── Resumes (Phase 8.4) ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE resumes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            label VARCHAR(255) NOT NULL,
            resume_text TEXT NOT NULL,
            embedding vector(768),
            is_active BOOLEAN NOT NULL DEFAULT false,
            uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    # ── Company logo_url (Phase 8.5) ────────────────────────────────────────
    op.add_column("companies", sa.Column("logo_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "logo_url")
    op.drop_index("ix_resumes_user_id", "resumes")
    op.drop_table("resumes")
    op.drop_index("ix_job_alerts_user_id", "job_alerts")
    op.drop_table("job_alerts")
