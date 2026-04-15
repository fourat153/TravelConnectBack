"""fix code column to string

Revision ID: 08111718997f
Revises: aecdd1fbbcac
Create Date: 2026-04-12 17:41:46.262904

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08111718997f'
down_revision: Union[str, Sequence[str], None] = 'aecdd1fbbcac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.alter_column('confirmation_code', 'code',
        existing_type=sa.String(6),
        type_=sa.String(),
        existing_nullable=False
    )

def downgrade() -> None:
    op.alter_column('confirmation_code', 'code',
        existing_type=sa.String(),
        type_=sa.String(6),
        existing_nullable=False
    )