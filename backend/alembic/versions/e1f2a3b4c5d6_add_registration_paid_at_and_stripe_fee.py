"""Record when a registration was paid, and the Stripe charge and fee.

Finnova (the association's finance app) books ticket revenue on the day it was
paid, gross and net of Stripe's fee.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-11-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('registrations', sa.Column('paid_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('registrations', sa.Column('paid_at_estimated', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('registrations', sa.Column('stripe_charge_id', sa.String(length=255), nullable=True))
    op.add_column('registrations', sa.Column('stripe_fee_cents', sa.Integer(), nullable=True))
    op.create_index('ix_registrations_paid_at', 'registrations', ['paid_at'])


def downgrade() -> None:
    op.drop_index('ix_registrations_paid_at', table_name='registrations')
    op.drop_column('registrations', 'stripe_fee_cents')
    op.drop_column('registrations', 'stripe_charge_id')
    op.drop_column('registrations', 'paid_at_estimated')
    op.drop_column('registrations', 'paid_at')
