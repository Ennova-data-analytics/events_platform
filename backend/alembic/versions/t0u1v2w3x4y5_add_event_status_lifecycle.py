"""Make events.status a real lifecycle: backfill existing rows to Published

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2026-08-31 00:00:00.000000

Until now `events.status` defaulted to 'Draft' and was never read: the public
event list returned every row regardless. This revision makes the column
meaningful, so the API can serve published events only.

The backfill below is the important part. Every existing event sits at the
'Draft' default, so without it the public site would empty out the moment the
new filtering ships.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 't0u1v2w3x4y5'
down_revision: Union[str, None] = 's9t0u1v2w3x4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALID_STATUSES = ('Draft', 'Published', 'Cancelled', 'Archived')


def upgrade() -> None:
    # Everything that exists today was live, so it becomes Published. This runs
    # first: the constraint below would reject any stray value otherwise.
    op.execute(
        "UPDATE events SET status = 'Published' "
        f"WHERE status IS NULL OR status NOT IN {VALID_STATUSES}"
    )

    op.create_check_constraint(
        'check_event_status_valid',
        'events',
        f"status IN {VALID_STATUSES}",
    )
    op.create_index('ix_events_status', 'events', ['status'])


def downgrade() -> None:
    op.drop_index('ix_events_status', table_name='events')
    op.drop_constraint('check_event_status_valid', 'events', type_='check')
