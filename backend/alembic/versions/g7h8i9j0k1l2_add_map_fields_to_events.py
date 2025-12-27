"""add map fields to events

Revision ID: g7h8i9j0k1l2
Revises: f1g2h3i4j5k6
Create Date: 2025-12-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g7h8i9j0k1l2'
down_revision = 'f1g2h3i4j5k6'
branch_labels = None
depends_on = None


def upgrade():
    """Add map-related fields to events table."""
    # Add map_address column for specific address used in geocoding
    op.add_column('events', sa.Column('map_address', sa.String(length=500), nullable=True))

    # Add latitude column for manual coordinate entry
    op.add_column('events', sa.Column('latitude', sa.Float(), nullable=True))

    # Add longitude column for manual coordinate entry
    op.add_column('events', sa.Column('longitude', sa.Float(), nullable=True))


def downgrade():
    """Remove map-related fields from events table."""
    op.drop_column('events', 'longitude')
    op.drop_column('events', 'latitude')
    op.drop_column('events', 'map_address')