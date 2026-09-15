"""merge migration heads

Revision ID: 64164b02752c
Revises: 4de228f31ed9, 7f1b8c9d4e2a
Create Date: 2026-08-07 11:06:09.729726

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64164b02752c'
down_revision: Union[str, Sequence[str], None] = ('4de228f31ed9', '7f1b8c9d4e2a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
