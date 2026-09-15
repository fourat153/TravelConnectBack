"""add device tokens and notifications

Revision ID: d2f7a8b9c0e1
Revises: 64164b02752c
Create Date: 2026-08-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2f7a8b9c0e1"
down_revision: Union[str, Sequence[str], None] = "64164b02752c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


notification_type = sa.Enum(
    "POST_LIKE",
    "POST_COMMENT",
    "FRIEND_REQUEST",
    "FRIEND_REQUEST_ACCEPTED",
    name="notificationtype",
)


def upgrade() -> None:
    op.create_table(
        "device_token",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_device_token_user_id", "device_token", ["user_id"])

    op.create_table(
        "notification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recipient_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_recipient_id", "notification", ["recipient_id"])
    op.create_index("ix_notification_created_at", "notification", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_notification_created_at", table_name="notification")
    op.drop_index("ix_notification_recipient_id", table_name="notification")
    op.drop_table("notification")
    op.drop_index("ix_device_token_user_id", table_name="device_token")
    op.drop_table("device_token")
    notification_type.drop(op.get_bind(), checkfirst=True)