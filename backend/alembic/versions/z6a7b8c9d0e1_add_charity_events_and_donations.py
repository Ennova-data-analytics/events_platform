"""Add charity events and optional donations on registrations

Revision ID: z6a7b8c9d0e1
Revises: y5z6a7b8c9d0
Create Date: 2026-10-13 00:00:00.000000

is_charitable gets a server default so existing events backfill to false.
donation_amount_euros is nullable with no backfill: null means no donation,
which is true of every existing registration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'z6a7b8c9d0e1'
down_revision: Union[str, None] = 'y5z6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('events', sa.Column('is_charitable', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('events', sa.Column('charity_name', sa.String(length=255), nullable=True))
    op.add_column('events', sa.Column('charity_description', sa.Text(), nullable=True))

    op.add_column('registrations', sa.Column('donation_amount_euros', sa.DECIMAL(precision=10, scale=2), nullable=True))
    op.create_check_constraint(
        'check_registration_donation_non_negative',
        'registrations',
        'donation_amount_euros IS NULL OR donation_amount_euros >= 0',
    )


def downgrade() -> None:
    op.drop_constraint('check_registration_donation_non_negative', 'registrations', type_='check')
    op.drop_column('registrations', 'donation_amount_euros')

    op.drop_column('events', 'charity_description')
    op.drop_column('events', 'charity_name')
    op.drop_column('events', 'is_charitable')
