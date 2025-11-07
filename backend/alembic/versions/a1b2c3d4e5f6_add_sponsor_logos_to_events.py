"""add sponsor_logos to events

Revision ID: a1b2c3d4e5f6
Revises: 2d9318229153
Create Date: 2025-11-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '2d9318229153'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add sponsor_logos column to events table.

    This column stores an array of S3 keys for sponsor logo images
    that will be displayed on the event page.
    """
    op.add_column('events',
        sa.Column('sponsor_logos', postgresql.ARRAY(sa.Text()), nullable=True)
    )


def downgrade() -> None:
    """Remove sponsor_logos column from events table."""
    op.drop_column('events', 'sponsor_logos')
