"""add group pricing and team invites

Revision ID: q7r8s9t0u1v2
Revises: p6q7r8s9t0u1
Create Date: 2026-03-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

revision = 'q7r8s9t0u1v2'
down_revision = 'p6q7r8s9t0u1'
branch_labels = None
depends_on = None


def upgrade():
    # Add group pricing columns to ticket_types
    op.add_column('ticket_types', sa.Column('group_payment_mode', sa.String(20), nullable=True))
    op.add_column('ticket_types', sa.Column('group_size', sa.Integer(), nullable=True))
    op.add_column('ticket_types', sa.Column('group_price_euros', sa.DECIMAL(10, 2), nullable=True))

    op.create_check_constraint(
        'check_group_size_gt_one', 'ticket_types', 'group_size IS NULL OR group_size > 1'
    )
    op.create_check_constraint(
        'check_group_price_non_negative', 'ticket_types', 'group_price_euros IS NULL OR group_price_euros >= 0'
    )
    op.create_check_constraint(
        'check_group_payment_mode_valid', 'ticket_types',
        "group_payment_mode IS NULL OR group_payment_mode IN ('leader', 'individual')"
    )

    # Create team_invites table
    op.create_table(
        'team_invites',
        sa.Column('invite_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('team_id', sa.Integer(), nullable=False, index=True),
        sa.Column('event_id', sa.Integer(), nullable=False, index=True),
        sa.Column('ticket_type_id', sa.Integer(), nullable=False),
        sa.Column('invited_email', sa.String(255), nullable=False),
        sa.Column('token', sa.String(128), nullable=False),
        sa.Column('claimed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('claimed_by_user_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),

        sa.ForeignKeyConstraint(['team_id'], ['event_teams.team_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_id'], ['events.event_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ticket_type_id'], ['ticket_types.ticket_type_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['claimed_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
    )
    op.create_index('ix_team_invites_token', 'team_invites', ['token'], unique=True)


def downgrade():
    op.drop_index('ix_team_invites_token', 'team_invites')
    op.drop_table('team_invites')

    op.drop_constraint('check_group_payment_mode_valid', 'ticket_types', type_='check')
    op.drop_constraint('check_group_price_non_negative', 'ticket_types', type_='check')
    op.drop_constraint('check_group_size_gt_one', 'ticket_types', type_='check')
    op.drop_column('ticket_types', 'group_price_euros')
    op.drop_column('ticket_types', 'group_size')
    op.drop_column('ticket_types', 'group_payment_mode')
