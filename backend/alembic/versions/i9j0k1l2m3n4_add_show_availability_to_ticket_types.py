"""add show_availability to ticket_types

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-01-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'i9j0k1l2m3n4'
down_revision = 'h8i9j0k1l2m3'
branch_labels = None
depends_on = None


def upgrade():
    # Add show_availability column to ticket_types table
    op.add_column(
        'ticket_types',
        sa.Column('show_availability', sa.Boolean(), nullable=False, server_default='true')
    )


def downgrade():
    # Drop show_availability column from ticket_types table
    op.drop_column('ticket_types', 'show_availability')
