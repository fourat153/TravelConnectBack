"""seed friendship status rows

Revision ID: c5d3a6f1e4b2
Revises: b7a4b43f8e2d
Create Date: 2026-05-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d3a6f1e4b2'
down_revision: Union[str, Sequence[str], None] = 'b7a4b43f8e2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


friendship_status_table = sa.table(
    'friendship_status',
    sa.column('name', sa.Enum('pending', 'accepted', 'refused', name='friendshipstatusenum')),
)


def upgrade() -> None:
    op.bulk_insert(
        friendship_status_table,
        [
            {'name': 'pending'},
            {'name': 'accepted'},
            {'name': 'refused'},
        ],
    )


def downgrade() -> None:
    op.execute(
        friendship_status_table.delete().where(
            friendship_status_table.c.name.in_(['pending', 'accepted', 'refused'])
        )
    )
