"""Let a department close recruitment before the rest of its cohort

Revision ID: y5z6a7b8c9d0
Revises: x4y5z6a7b8c9
Create Date: 2026-09-23 00:00:00.000000

Nullable with no backfill: null means the department closes with the cohort,
which is how every existing membership already behaves.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'y5z6a7b8c9d0'
down_revision: Union[str, None] = 'x4y5z6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cycle_departments', sa.Column('closes_at', sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('cycle_departments', 'closes_at')
