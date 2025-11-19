"""add ennova member support

Revision ID: d9e0f1g2h3i4
Revises: c8d9e0f1g2h3
Create Date: 2025-11-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9e0f1g2h3i4'
down_revision: Union[str, Sequence[str], None] = 'c8d9e0f1g2h3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Ennova member support.

    Adds is_ennova_member flag to users table to track Ennova association members.
    Adds is_free_for_members flag to events table to mark events that are free for members.
    Adds member_discount_applied flag to registrations table to track when member benefit was applied.
    """
    # Add is_ennova_member to users table
    op.add_column('users', sa.Column('is_ennova_member', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index(op.f('ix_users_is_ennova_member'), 'users', ['is_ennova_member'], unique=False)

    # Add is_free_for_members to events table
    op.add_column('events', sa.Column('is_free_for_members', sa.Boolean(), nullable=False, server_default='false'))

    # Add member_discount_applied to registrations table
    op.add_column('registrations', sa.Column('member_discount_applied', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Remove Ennova member support."""
    op.drop_column('registrations', 'member_discount_applied')
    op.drop_column('events', 'is_free_for_members')
    op.drop_index(op.f('ix_users_is_ennova_member'), table_name='users')
    op.drop_column('users', 'is_ennova_member')