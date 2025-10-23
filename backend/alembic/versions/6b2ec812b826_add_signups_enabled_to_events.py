"""add_signups_enabled_to_events

Revision ID: 6b2ec812b826
Revises: 57891b0ac72c
Create Date: 2025-10-23 23:01:48.026139

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b2ec812b826'
down_revision: Union[str, Sequence[str], None] = '57891b0ac72c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('events', sa.Column('signups_enabled', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('events', 'signups_enabled')
