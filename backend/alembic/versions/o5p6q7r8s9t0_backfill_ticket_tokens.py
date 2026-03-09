"""backfill ticket tokens for existing approved/paid registrations

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-03-08 00:00:00.000000

"""
from typing import Sequence, Union

import secrets
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision: str = 'o5p6q7r8s9t0'
down_revision: Union[str, None] = 'n4o5p6q7r8s9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Fetch IDs of all confirmed registrations missing a ticket token
    result = conn.execute(
        text(
            "SELECT registration_id FROM registrations "
            "WHERE status IN ('Paid', 'Approved') AND ticket_token IS NULL"
        )
    )
    rows = result.fetchall()

    for (registration_id,) in rows:
        token = secrets.token_urlsafe(32)
        conn.execute(
            text(
                "UPDATE registrations SET ticket_token = :token "
                "WHERE registration_id = :rid"
            ),
            {"token": token, "rid": registration_id},
        )


def downgrade() -> None:
    # Tokens added by this migration cannot be safely identified — no-op
    pass
