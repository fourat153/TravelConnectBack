"""add post author and delete cascades

Revision ID: k9a0b1c2d3e4
Revises: j8e9f0a1b2c3
Create Date: 2026-10-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "j8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add posts.user_id (author) plus database-level delete cascades."""
    op.add_column("posts", sa.Column("user_id", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE posts
        SET user_id = trips.user_id
        FROM stops
        JOIN trips ON stops.trip_id = trips.id
        WHERE posts.stop_id = stops.id
        """
    )

    op.alter_column("posts", "user_id", nullable=False)
    op.create_foreign_key(
        "posts_user_id_fkey",
        "posts",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("posts_stop_id_fkey", "posts", type_="foreignkey")
    op.create_foreign_key(
        "posts_stop_id_fkey",
        "posts",
        "stops",
        ["stop_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("stops_trip_id_fkey", "stops", type_="foreignkey")
    op.create_foreign_key(
        "stops_trip_id_fkey",
        "stops",
        "trips",
        ["trip_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Revert cascades and drop the post author column."""
    op.drop_constraint("stops_trip_id_fkey", "stops", type_="foreignkey")
    op.create_foreign_key(
        "stops_trip_id_fkey", "stops", "trips", ["trip_id"], ["id"]
    )

    op.drop_constraint("posts_stop_id_fkey", "posts", type_="foreignkey")
    op.create_foreign_key(
        "posts_stop_id_fkey", "posts", "stops", ["stop_id"], ["id"]
    )

    op.drop_constraint("posts_user_id_fkey", "posts", type_="foreignkey")
    op.drop_column("posts", "user_id")
