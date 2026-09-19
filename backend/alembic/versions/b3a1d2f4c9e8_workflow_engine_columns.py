"""workflow engine columns

Revision ID: b3a1d2f4c9e8
Revises: 3394fe8b6917
Create Date: 2026-09-19 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3a1d2f4c9e8'
down_revision: Union[str, Sequence[str], None] = '3394fe8b6917'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add multi-workflow engine columns to agencies."""
    op.add_column('agencies', sa.Column('workflow_type', sa.String(length=40), nullable=False, server_default='domestic_it'))
    op.add_column('agencies', sa.Column('workflow_config', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Drop workflow engine columns."""
    op.drop_column('agencies', 'workflow_config')
    op.drop_column('agencies', 'workflow_type')