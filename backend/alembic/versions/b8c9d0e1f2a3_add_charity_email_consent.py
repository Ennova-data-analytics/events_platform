"""Add optional consent to emails from an event's charity

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-30 00:00:00.000001

Organisers switch this on per charity event; attendees then answer at sign-up.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('events', sa.Column('charity_email_consent_enabled', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('registrations', sa.Column('charity_email_consent', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('registrations', sa.Column('charity_email_consent_at', sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('registrations', 'charity_email_consent_at')
    op.drop_column('registrations', 'charity_email_consent')
    op.drop_column('events', 'charity_email_consent_enabled')
