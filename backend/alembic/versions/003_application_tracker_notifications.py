"""Application tracker columns + notification prefs on profiles

Revision ID: 003
Revises: 002
Create Date: 2026-03-26
"""
import sqlalchemy as sa

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Notification preferences on profiles
    op.add_column("profiles", sa.Column("notifications_enabled", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("profiles", sa.Column("notification_email", sa.String(255), nullable=True))
    op.add_column("profiles", sa.Column("notification_min_score", sa.Float(), server_default="0.8", nullable=False))
    op.add_column("profiles", sa.Column("last_notified_at", sa.DateTime(timezone=True), nullable=True))

    # Index on applications so status queries are fast
    op.create_index("ix_applications_status", "applications", ["status"])


def downgrade() -> None:
    op.drop_index("ix_applications_status", "applications")
    op.drop_column("profiles", "last_notified_at")
    op.drop_column("profiles", "notification_min_score")
    op.drop_column("profiles", "notification_email")
    op.drop_column("profiles", "notifications_enabled")
