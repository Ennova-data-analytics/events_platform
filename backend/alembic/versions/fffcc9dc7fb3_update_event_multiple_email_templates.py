"""update_event_multiple_email_templates

Revision ID: fffcc9dc7fb3
Revises: c2e9b6aee84a
Create Date: 2025-10-21 09:02:31.630886

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fffcc9dc7fb3'
down_revision: Union[str, Sequence[str], None] = 'c2e9b6aee84a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the old single email_template_id column and its foreign key
    op.drop_constraint('fk_events_email_template_id', 'events', type_='foreignkey')
    op.drop_column('events', 'email_template_id')

    # Add new columns for each email template type
    op.add_column('events', sa.Column('email_template_approved_id', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('email_template_rejected_id', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('email_template_received_id', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('email_template_payment_id', sa.Integer(), nullable=True))

    # Create foreign keys for each new column
    op.create_foreign_key(
        'fk_events_email_template_approved_id',
        'events', 'email_templates',
        ['email_template_approved_id'], ['template_id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_events_email_template_rejected_id',
        'events', 'email_templates',
        ['email_template_rejected_id'], ['template_id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_events_email_template_received_id',
        'events', 'email_templates',
        ['email_template_received_id'], ['template_id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_events_email_template_payment_id',
        'events', 'email_templates',
        ['email_template_payment_id'], ['template_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop all new foreign keys
    op.drop_constraint('fk_events_email_template_approved_id', 'events', type_='foreignkey')
    op.drop_constraint('fk_events_email_template_rejected_id', 'events', type_='foreignkey')
    op.drop_constraint('fk_events_email_template_received_id', 'events', type_='foreignkey')
    op.drop_constraint('fk_events_email_template_payment_id', 'events', type_='foreignkey')

    # Drop all new columns
    op.drop_column('events', 'email_template_approved_id')
    op.drop_column('events', 'email_template_rejected_id')
    op.drop_column('events', 'email_template_received_id')
    op.drop_column('events', 'email_template_payment_id')

    # Add back the old column
    op.add_column('events', sa.Column('email_template_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_events_email_template_id',
        'events', 'email_templates',
        ['email_template_id'], ['template_id'],
        ondelete='SET NULL'
    )
