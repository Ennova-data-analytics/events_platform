"""Count ticket seats from the registrations

Revision ID: g3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-11-23 00:00:00.000000

ticket_types.tickets_sold was a running total, bumped only when a registration
became Paid. Sign-up checked capacity against a different count (every
registration not cancelled), so the event page could show seats left while
sign-up said it was sold out. Seats are now always counted from the
registrations (see models.seats_taken_expression), so the column goes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'g3b4c5d6e7f8'
down_revision: Union[str, None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('check_tickets_sold_non_negative', 'ticket_types', type_='check')
    op.drop_column('ticket_types', 'tickets_sold')


def downgrade() -> None:
    op.add_column(
        'ticket_types',
        sa.Column('tickets_sold', sa.Integer(), nullable=False, server_default='0'),
    )
    # Refill it with the seats taken, the closest thing to what it tracked.
    op.execute("""
        UPDATE ticket_types tt SET tickets_sold =
            (SELECT count(*) FROM registrations r
              WHERE r.ticket_type_id = tt.ticket_type_id
                AND r.status IN ('Approved', 'Paid'))
          + (SELECT count(*) FROM friend_tickets ft
               JOIN registrations b ON b.registration_id = ft.buyer_registration_id
              WHERE b.ticket_type_id = tt.ticket_type_id
                AND b.status IN ('Approved', 'Paid')
                AND ft.status <> 'claimed')
    """)
    op.create_check_constraint('check_tickets_sold_non_negative', 'ticket_types', 'tickets_sold >= 0')
