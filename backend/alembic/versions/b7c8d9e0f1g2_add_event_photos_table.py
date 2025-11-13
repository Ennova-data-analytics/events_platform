"""add event_photos table

Revision ID: b7c8d9e0f1g2
Revises: a1b2c3d4e5f6
Create Date: 2025-11-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1g2'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create event_photos table for storing multiple photos per event.

    This allows events to have photo galleries from past events,
    with support for captions, ordering, and tracking of uploads.
    """
    op.create_table(
        'event_photos',
        sa.Column('photo_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('photo_url', sa.Text(), nullable=False),
        sa.Column('caption', sa.String(500), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('uploaded_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('uploaded_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('photo_id'),
        sa.ForeignKeyConstraint(
            ['event_id'],
            ['events.event_id'],
            name='fk_event_photos_event_id',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['uploaded_by_user_id'],
            ['users.user_id'],
            name='fk_event_photos_uploaded_by_user_id',
            ondelete='SET NULL'
        )
    )

    # Create index on event_id for faster queries
    op.create_index(
        'ix_event_photos_event_id',
        'event_photos',
        ['event_id']
    )

    # Create index on display_order for sorted queries
    op.create_index(
        'ix_event_photos_display_order',
        'event_photos',
        ['event_id', 'display_order']
    )


def downgrade() -> None:
    """Remove event_photos table."""
    op.drop_index('ix_event_photos_display_order', table_name='event_photos')
    op.drop_index('ix_event_photos_event_id', table_name='event_photos')
    op.drop_table('event_photos')
