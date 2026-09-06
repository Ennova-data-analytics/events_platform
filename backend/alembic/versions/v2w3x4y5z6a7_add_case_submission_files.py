"""Let candidates submit their case response as an uploaded file

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-09-06 00:00:00.000000

applications.case_submission_url already existed for a link. These add the
file equivalent, mirroring the case brief columns. Both nullable, no backfill.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'v2w3x4y5z6a7'
down_revision: Union[str, None] = 'u1v2w3x4y5z6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('applications', sa.Column('case_submission_s3_key', sa.Text(), nullable=True))
    op.add_column('applications', sa.Column('case_submission_filename', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('applications', 'case_submission_filename')
    op.drop_column('applications', 'case_submission_s3_key')
