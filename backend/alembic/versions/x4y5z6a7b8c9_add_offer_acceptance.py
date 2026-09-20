"""Let candidates accept or decline offers, locking their other applications

Revision ID: x4y5z6a7b8c9
Revises: w3x4y5z6a7b8
Create Date: 2026-09-19 00:00:00.000000

A recruiter now sends an offer ('offered') and the candidate answers it from
their status page. Accepting locks the candidate's other open applications this
cycle: they keep their stage and history but can no longer be acted on.

All columns are nullable with no backfill. Existing 'accepted' rows predate the
candidate's say and are left as they are; their siblings are not locked.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'x4y5z6a7b8c9'
down_revision: Union[str, None] = 'w3x4y5z6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('applications', sa.Column('offer_sent_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('applications', sa.Column('offer_expires_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('applications', sa.Column('offer_responded_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('applications', sa.Column('locked_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('applications', sa.Column('locked_by_application_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_applications_locked_by_application', 'applications', 'applications',
        ['locked_by_application_id'], ['application_id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_applications_locked_by_application', 'applications', type_='foreignkey')
    op.drop_column('applications', 'locked_by_application_id')
    op.drop_column('applications', 'locked_at')
    op.drop_column('applications', 'offer_responded_at')
    op.drop_column('applications', 'offer_expires_at')
    op.drop_column('applications', 'offer_sent_at')
