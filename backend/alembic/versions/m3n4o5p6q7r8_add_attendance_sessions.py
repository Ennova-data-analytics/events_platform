"""add attendance sessions

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-02-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'm3n4o5p6q7r8'
down_revision: Union[str, Sequence[str], None] = 'l2m3n4o5p6q7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'attendance_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('frozen_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('total_checked_in', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.event_id'], ondelete='CASCADE'),
    )
    op.create_index('ix_attendance_sessions_id', 'attendance_sessions', ['id'])
    op.create_index('ix_attendance_sessions_event_id', 'attendance_sessions', ['event_id'])

    op.create_table(
        'attendance_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('registration_id', sa.Integer(), nullable=True),
        sa.Column('guest_ticket_id', sa.Integer(), nullable=True),
        sa.Column('attendee_name', sa.String(length=200), nullable=False),
        sa.Column('checked_in', sa.Boolean(), nullable=False),
        sa.Column('checked_in_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['attendance_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['registration_id'], ['registrations.registration_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['guest_ticket_id'], ['guest_tickets.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_attendance_records_id', 'attendance_records', ['id'])
    op.create_index('ix_attendance_records_session_id', 'attendance_records', ['session_id'])


def downgrade() -> None:
    op.drop_index('ix_attendance_records_session_id', table_name='attendance_records')
    op.drop_index('ix_attendance_records_id', table_name='attendance_records')
    op.drop_table('attendance_records')
    op.drop_index('ix_attendance_sessions_event_id', table_name='attendance_sessions')
    op.drop_index('ix_attendance_sessions_id', table_name='attendance_sessions')
    op.drop_table('attendance_sessions')
