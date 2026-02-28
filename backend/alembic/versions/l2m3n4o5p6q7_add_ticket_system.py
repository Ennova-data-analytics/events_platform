"""add ticket system

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-02-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'l2m3n4o5p6q7'
down_revision: Union[str, Sequence[str], None] = 'k1l2m3n4o5p6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ticket fields to registrations
    op.add_column('registrations', sa.Column('ticket_token', sa.String(length=64), nullable=True, unique=True))
    op.add_column('registrations', sa.Column('checked_in', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('registrations', sa.Column('checked_in_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.create_index('ix_registrations_ticket_token', 'registrations', ['ticket_token'], unique=True)

    # Create guest_tickets table
    op.create_table(
        'guest_tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('guest_name', sa.String(length=200), nullable=False),
        sa.Column('guest_email', sa.String(length=200), nullable=False),
        sa.Column('ticket_token', sa.String(length=64), nullable=False, unique=True),
        sa.Column('checked_in', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('checked_in_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by_user_id', UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.event_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
    )
    op.create_index('ix_guest_tickets_id', 'guest_tickets', ['id'])
    op.create_index('ix_guest_tickets_event_id', 'guest_tickets', ['event_id'])
    op.create_index('ix_guest_tickets_ticket_token', 'guest_tickets', ['ticket_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_guest_tickets_ticket_token', table_name='guest_tickets')
    op.drop_index('ix_guest_tickets_event_id', table_name='guest_tickets')
    op.drop_index('ix_guest_tickets_id', table_name='guest_tickets')
    op.drop_table('guest_tickets')
    op.drop_index('ix_registrations_ticket_token', table_name='registrations')
    op.drop_column('registrations', 'checked_in_at')
    op.drop_column('registrations', 'checked_in')
    op.drop_column('registrations', 'ticket_token')