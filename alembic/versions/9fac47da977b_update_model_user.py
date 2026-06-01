from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '9fac47da977b'
down_revision: Union[str, Sequence[str], None] = 'd89be824f207'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

confirmed_enum = postgresql.ENUM('Confirmed', 'NotConfirmed', name='confirmedenum')

def upgrade() -> None:
    op.create_table('error_logger',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('orig', sa.String(), nullable=True),
        sa.Column('statement', sa.String(), nullable=True),
        sa.Column('params', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    confirmed_enum.create(op.get_bind(), checkfirst=True)

    op.alter_column('user', 'is_confirmed',
        existing_type=sa.INTEGER(),
        type_=sa.Enum('Confirmed', 'NotConfirmed', name='confirmedenum'),
        existing_nullable=False,
        postgresql_using="CASE is_confirmed WHEN 1 THEN 'Confirmed'::confirmedenum ELSE 'NotConfirmed'::confirmedenum END"
    )

def downgrade() -> None:
    op.alter_column('user', 'is_confirmed',
        existing_type=sa.Enum('Confirmed', 'NotConfirmed', name='confirmedenum'),
        type_=sa.INTEGER(),
        existing_nullable=False,
        postgresql_using="CASE is_confirmed WHEN 'Confirmed' THEN 1 ELSE 0 END"
    )
    op.drop_table('error_logger')
    confirmed_enum.drop(op.get_bind(), checkfirst=True)