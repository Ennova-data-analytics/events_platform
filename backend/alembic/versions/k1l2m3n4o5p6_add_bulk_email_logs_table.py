"""add bulk_email_logs table

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-02-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, Sequence[str], None] = 'j0k1l2m3n4o5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bulk_email_logs',
        sa.Column('log_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('sent_by_user_id', UUID(as_uuid=True), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('recipient_statuses', sa.ARRAY(sa.String()), nullable=False),
        sa.Column('sent_to_emails', sa.ARRAY(sa.String()), server_default='{}'),
        sa.Column('total_sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_emails', sa.ARRAY(sa.String()), server_default='{}'),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('log_id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.event_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sent_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
    )
    op.create_index('ix_bulk_email_logs_event_id', 'bulk_email_logs', ['event_id'])
    op.create_index('ix_bulk_email_logs_log_id', 'bulk_email_logs', ['log_id'])


def downgrade() -> None:
    op.drop_index('ix_bulk_email_logs_log_id', table_name='bulk_email_logs')
    op.drop_index('ix_bulk_email_logs_event_id', table_name='bulk_email_logs')
    op.drop_table('bulk_email_logs')
