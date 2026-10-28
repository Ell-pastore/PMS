"""Add tenant-scoped in-app notification preferences.

Revision ID: e7f9a1c3b5d7
Revises: c4d6e8f0a1b2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7f9a1c3b5d7"
down_revision: Union[str, None] = "c4d6e8f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("university_id", sa.Uuid(), nullable=False),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), server_default="in_app", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["user_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            name="fk_notification_preferences_membership",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "user_id",
            "university_id",
            "notification_type",
            "channel",
            name="uq_notification_preferences_user_university_type_channel",
        ),
        sa.CheckConstraint(
            "length(btrim(notification_type)) > 0",
            name="ck_notification_preferences_type_nonempty",
        ),
        sa.CheckConstraint(
            "channel = 'in_app'",
            name="ck_notification_preferences_channel",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
