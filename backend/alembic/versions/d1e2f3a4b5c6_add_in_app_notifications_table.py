"""add in app notifications table

Revision ID: d1e2f3a4b5c6
Revises: 33cdc5388396
Create Date: 2025-10-08 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = '33cdc5388396'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create in_app_notifications table"""
    op.create_table(
        'in_app_notifications',
        sa.Column('notification_id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('related_entity_type', sa.String(50), nullable=True),
        sa.Column('related_entity_id', sa.Integer(), nullable=True),
        sa.Column('is_read', sa.Boolean(), default=False, nullable=False, index=True),
        sa.Column('read_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
    )

    # Create composite index for performance
    op.create_index('ix_notifications_user_read', 'in_app_notifications', ['user_id', 'is_read'])


def downgrade() -> None:
    """Downgrade schema - drop in_app_notifications table"""
    op.drop_index('ix_notifications_user_read', table_name='in_app_notifications')
    op.drop_table('in_app_notifications')