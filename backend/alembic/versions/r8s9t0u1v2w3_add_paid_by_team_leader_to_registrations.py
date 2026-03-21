"""add paid_by_team_leader to registrations

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-03-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'r8s9t0u1v2w3'
down_revision = 'q7r8s9t0u1v2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'registrations',
        sa.Column('paid_by_team_leader', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade():
    op.drop_column('registrations', 'paid_by_team_leader')
