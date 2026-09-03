"""Allow a case brief to be an uploaded PDF, not only a link

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2026-09-03 00:00:00.000000

Departments carry a reusable default brief; applications snapshot whichever
brief was actually sent, so replacing the department's file later doesn't change
what an already-emailed candidate receives.

All four columns are nullable with no backfill: existing applications keep
working off case_brief_url exactly as before.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'u1v2w3x4y5z6'
down_revision: Union[str, None] = 't0u1v2w3x4y5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('departments', sa.Column('case_brief_s3_key', sa.Text(), nullable=True))
    op.add_column('departments', sa.Column('case_brief_filename', sa.String(255), nullable=True))

    op.add_column('applications', sa.Column('case_brief_s3_key', sa.Text(), nullable=True))
    op.add_column('applications', sa.Column('case_brief_filename', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('applications', 'case_brief_filename')
    op.drop_column('applications', 'case_brief_s3_key')
    op.drop_column('departments', 'case_brief_filename')
    op.drop_column('departments', 'case_brief_s3_key')
