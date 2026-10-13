"""Add standalone donations to charity events

Revision ID: a7b8c9d0e1f2
Revises: z6a7b8c9d0e1
Create Date: 2026-10-13 00:00:00.000001

A donation made without registering for the event. The donor needs no account,
so the row is keyed on email with an optional user_id.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'z6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'donations',
        sa.Column('donation_id', sa.Integer(), primary_key=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.event_id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('amount_euros', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='Pending'),
        sa.Column('stripe_checkout_session_id', sa.String(length=255), nullable=True, unique=True),
        sa.Column('stripe_payment_intent_id', sa.String(length=255), nullable=True, unique=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('paid_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint('amount_euros > 0', name='check_donation_amount_positive'),
        sa.CheckConstraint("status IN ('Pending', 'Paid')", name='check_donation_status_valid'),
    )
    op.create_index('ix_donations_event_id', 'donations', ['event_id'])


def downgrade() -> None:
    op.drop_index('ix_donations_event_id', table_name='donations')
    op.drop_table('donations')
