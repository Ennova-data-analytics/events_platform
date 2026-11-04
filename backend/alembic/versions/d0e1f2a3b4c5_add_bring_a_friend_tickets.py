"""add bring-a-friend tickets, and team invite sent_at

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-11-04

"""
from alembic import op
import sqlalchemy as sa


revision = 'd0e1f2a3b4c5'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'ticket_types',
        sa.Column('bring_a_friend', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_check_constraint(
        'check_bring_a_friend_standalone',
        'ticket_types',
        "NOT bring_a_friend OR (group_payment_mode IS NULL AND NOT requires_team AND NOT is_free_for_members)",
    )

    # Invites already in the table were emailed when they were created.
    op.add_column('team_invites', sa.Column('sent_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.execute("UPDATE team_invites SET sent_at = created_at")

    op.create_table(
        'friend_tickets',
        sa.Column('friend_ticket_id', sa.Integer(), primary_key=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.event_id', ondelete='CASCADE'), nullable=False),
        sa.Column('buyer_registration_id', sa.Integer(),
                  sa.ForeignKey('registrations.registration_id', ondelete='CASCADE'), nullable=False),
        sa.Column('friend_email', sa.String(255), nullable=False),
        sa.Column('token', sa.String(128), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='awaiting_payment'),
        sa.Column('friend_registration_id', sa.Integer(),
                  sa.ForeignKey('registrations.registration_id', ondelete='SET NULL'), nullable=True),
        sa.Column('released_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_emailed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('reminder_sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('claimed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('buyer_registration_id', name='uq_friend_tickets_buyer_registration_id'),
        sa.UniqueConstraint('friend_registration_id', name='uq_friend_tickets_friend_registration_id'),
        sa.CheckConstraint("status IN ('awaiting_payment', 'sent', 'claimed')", name='check_friend_ticket_status_valid'),
        sa.CheckConstraint("(status = 'claimed') = (claimed_at IS NOT NULL)", name='check_friend_ticket_claimed_at'),
    )
    op.create_index('ix_friend_tickets_event_id', 'friend_tickets', ['event_id'])
    op.create_index('ix_friend_tickets_token', 'friend_tickets', ['token'], unique=True)


def downgrade():
    op.drop_index('ix_friend_tickets_token', table_name='friend_tickets')
    op.drop_index('ix_friend_tickets_event_id', table_name='friend_tickets')
    op.drop_table('friend_tickets')
    op.drop_column('team_invites', 'sent_at')
    op.drop_constraint('check_bring_a_friend_standalone', 'ticket_types', type_='check')
    op.drop_column('ticket_types', 'bring_a_friend')
