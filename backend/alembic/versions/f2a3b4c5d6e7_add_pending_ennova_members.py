"""Add pending Ennova members

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-11-09 00:00:00.000000

Emails from an imported members list that don't have an account yet. When
someone signs up with one of them they become an Ennova member and the row is
removed. Emails are stored lowercased, so the unique index is also the
case-insensitive lookup.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pending_ennova_members',
        sa.Column('pending_member_id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('source_filename', sa.String(length=255), nullable=True),
        sa.Column(
            'added_by_user_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True,
        ),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('email = lower(email)', name='check_pending_ennova_member_email_lowercase'),
    )
    op.create_index('ix_pending_ennova_members_email', 'pending_ennova_members', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_pending_ennova_members_email', table_name='pending_ennova_members')
    op.drop_table('pending_ennova_members')
