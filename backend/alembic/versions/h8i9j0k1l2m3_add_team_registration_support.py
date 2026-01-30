"""add team registration support

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-01-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP


# revision identifiers, used by Alembic.
revision = 'h8i9j0k1l2m3'
down_revision = 'g7h8i9j0k1l2'
branch_labels = None
depends_on = None


def upgrade():
    # Create event_teams table
    op.create_table(
        'event_teams',
        sa.Column('team_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.Integer(), nullable=False, index=True),
        sa.Column('team_name', sa.String(255), nullable=False),
        sa.Column('max_members', sa.Integer(), nullable=True),
        sa.Column('created_by_user_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),

        # Foreign keys
        sa.ForeignKeyConstraint(['event_id'], ['events.event_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.user_id'], ondelete='SET NULL'),

        # Unique constraint
        sa.UniqueConstraint('event_id', 'team_name', name='unique_team_name_per_event'),

        # Check constraints
        sa.CheckConstraint('max_members IS NULL OR max_members > 0', name='check_team_max_members_positive'),
    )

    # Create indexes for event_teams
    op.create_index('idx_event_teams_event_id', 'event_teams', ['event_id'])
    op.create_index('idx_event_teams_created_by', 'event_teams', ['created_by_user_id'])

    # Create team_members table
    op.create_table(
        'team_members',
        sa.Column('member_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('team_id', sa.Integer(), nullable=False, index=True),
        sa.Column('registration_id', sa.Integer(), nullable=False, index=True),
        sa.Column('joined_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),

        # Foreign keys
        sa.ForeignKeyConstraint(['team_id'], ['event_teams.team_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['registration_id'], ['registrations.registration_id'], ondelete='CASCADE'),

        # Unique constraint - one registration can only be in one team
        sa.UniqueConstraint('registration_id', name='unique_registration_per_team'),
    )

    # Create indexes for team_members
    op.create_index('idx_team_members_team_id', 'team_members', ['team_id'])
    op.create_index('idx_team_members_registration_id', 'team_members', ['registration_id'])

    # Add team fields to ticket_types table
    op.add_column(
        'ticket_types',
        sa.Column('requires_team', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column(
        'ticket_types',
        sa.Column('team_max_members', sa.Integer(), nullable=True)
    )

    # Add check constraint for team_max_members
    op.create_check_constraint(
        'check_ticket_team_max_members_positive',
        'ticket_types',
        'team_max_members IS NULL OR team_max_members > 0'
    )


def downgrade():
    # Drop check constraint from ticket_types
    op.drop_constraint('check_ticket_team_max_members_positive', 'ticket_types', type_='check')

    # Drop columns from ticket_types
    op.drop_column('ticket_types', 'team_max_members')
    op.drop_column('ticket_types', 'requires_team')

    # Drop indexes from team_members
    op.drop_index('idx_team_members_registration_id', 'team_members')
    op.drop_index('idx_team_members_team_id', 'team_members')

    # Drop team_members table
    op.drop_table('team_members')

    # Drop indexes from event_teams
    op.drop_index('idx_event_teams_created_by', 'event_teams')
    op.drop_index('idx_event_teams_event_id', 'event_teams')

    # Drop event_teams table
    op.drop_table('event_teams')
