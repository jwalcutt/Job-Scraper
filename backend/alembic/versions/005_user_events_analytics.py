"""User events table for implicit feedback and analytics

Revision ID: 005
Revises: 004
Create Date: 2026-04-01
"""
import sqlalchemy as sa

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_user_events_user_id", "user_events", ["user_id"])
    op.create_index("ix_user_events_job_id", "user_events", ["job_id"])
    op.create_index("ix_user_events_event_type", "user_events", ["event_type"])
    op.create_index(
        "ix_user_events_user_type",
        "user_events",
        ["user_id", "event_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_events_user_type", "user_events")
    op.drop_index("ix_user_events_event_type", "user_events")
    op.drop_index("ix_user_events_job_id", "user_events")
    op.drop_index("ix_user_events_user_id", "user_events")
    op.drop_table("user_events")
