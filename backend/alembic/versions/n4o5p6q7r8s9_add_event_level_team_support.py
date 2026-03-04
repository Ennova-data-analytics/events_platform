"""add event level team support

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-03-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'n4o5p6q7r8s9'
down_revision: Union[str, None] = 'm3n4o5p6q7r8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'events',
        sa.Column('teams_enabled', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column(
        'events',
        sa.Column('team_max_members', sa.Integer(), nullable=True)
    )
    op.create_check_constraint(
        'check_event_team_max_members_positive',
        'events',
        'team_max_members IS NULL OR team_max_members > 0'
    )


def downgrade() -> None:
    op.drop_constraint('check_event_team_max_members_positive', 'events', type_='check')
    op.drop_column('events', 'team_max_members')
    op.drop_column('events', 'teams_enabled')
