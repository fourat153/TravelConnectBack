"""merge_main_and_feed_migrations

Revision ID: 3bca933e1563
Revises: 436d7aa21e7a, 507fb12e4786
Create Date: 2026-06-01 11:28:16.916269

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3bca933e1563'
down_revision: Union[str, Sequence[str], None] = ('436d7aa21e7a', '507fb12e4786')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
