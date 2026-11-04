"""Add partial refunds and soft-deleted ticket types

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-11-04 00:00:00.000000

refunds records money given back on a ticket the holder keeps. Nothing to
backfill: no refund has been made through the platform before.

ticket_types.deleted_at is nullable with no backfill: null means not deleted,
which is true of every existing ticket type.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ticket_types', sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True))

    op.create_table(
        'refunds',
        sa.Column('refund_id', sa.Integer(), primary_key=True),
        sa.Column('registration_id', sa.Integer(), sa.ForeignKey('registrations.registration_id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.event_id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount_euros', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('method', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('stripe_refund_id', sa.String(length=255), nullable=True, unique=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('email_sent', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('amount_euros > 0', name='check_refund_amount_positive'),
        sa.CheckConstraint("method IN ('stripe', 'manual')", name='check_refund_method_valid'),
        sa.CheckConstraint("status IN ('pending', 'succeeded', 'failed')", name='check_refund_status_valid'),
        sa.UniqueConstraint('batch_id', 'registration_id', name='uq_refund_batch_registration'),
    )
    op.create_index('ix_refunds_registration_id', 'refunds', ['registration_id'])
    op.create_index('ix_refunds_event_id', 'refunds', ['event_id'])
    op.create_index('ix_refunds_batch_id', 'refunds', ['batch_id'])


def downgrade() -> None:
    op.drop_index('ix_refunds_batch_id', table_name='refunds')
    op.drop_index('ix_refunds_event_id', table_name='refunds')
    op.drop_index('ix_refunds_registration_id', table_name='refunds')
    op.drop_table('refunds')

    op.drop_column('ticket_types', 'deleted_at')
