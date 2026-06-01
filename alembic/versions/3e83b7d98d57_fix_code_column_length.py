"""fix code column length

Revision ID: 3e83b7d98d57
Revises: 9fac47da977b
Create Date: 2026-04-16 17:53:40.736544

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e83b7d98d57'
down_revision: Union[str, Sequence[str], None] = '9fac47da977b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column('confirmation_code', 'code',
        existing_type=sa.String(6),
        type_=sa.String(),   # unlimited, matches your model
        existing_nullable=False
    )

def downgrade():
    op.alter_column('confirmation_code', 'code',
        existing_type=sa.String(),
        type_=sa.String(6),
        existing_nullable=False
    )