"""add requires_approval to events

Revision ID: 2d9318229153
Revises: e5cb441e94fa
Create Date: 2025-10-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d9318229153'
down_revision: Union[str, Sequence[str], None] = 'e5cb441e94fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add requires_approval column to events table.

    This column controls whether registrations for an event need manual
    approval before payment. Default is True to maintain existing behavior.
    """
    # Add requires_approval column with default True to maintain current behavior
    op.add_column('events',
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='true')
    )


def downgrade() -> None:
    """Remove requires_approval column from events table."""
    # Remove requires_approval column
    op.drop_column('events', 'requires_approval')