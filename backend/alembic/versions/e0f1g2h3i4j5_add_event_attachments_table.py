"""add event_attachments table

Revision ID: e0f1g2h3i4j5
Revises: d9e0f1g2h3i4
Create Date: 2025-11-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e0f1g2h3i4j5'
down_revision: Union[str, Sequence[str], None] = 'd9e0f1g2h3i4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create event_attachments table for storing files attached to events.

    This allows organizers to upload presentations, guides, worksheets, and other
    documents that participants can download. Supports multiple files per event
    with ordering, descriptions, and audit tracking.
    """
    op.create_table(
        'event_attachments',
        sa.Column('attachment_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('file_url', sa.Text(), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('uploaded_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('uploaded_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('attachment_id'),
        sa.ForeignKeyConstraint(
            ['event_id'],
            ['events.event_id'],
            name='fk_event_attachments_event_id',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['uploaded_by_user_id'],
            ['users.user_id'],
            name='fk_event_attachments_uploaded_by_user_id',
            ondelete='SET NULL'
        )
    )

    # Create index on event_id for faster queries
    op.create_index(
        'ix_event_attachments_event_id',
        'event_attachments',
        ['event_id']
    )

    # Create index on display_order for sorted queries
    op.create_index(
        'ix_event_attachments_display_order',
        'event_attachments',
        ['event_id', 'display_order']
    )


def downgrade() -> None:
    """Remove event_attachments table."""
    op.drop_index('ix_event_attachments_display_order', table_name='event_attachments')
    op.drop_index('ix_event_attachments_event_id', table_name='event_attachments')
    op.drop_table('event_attachments')
