"""add discount codes

Revision ID: c8d9e0f1g2h3
Revises: b7c8d9e0f1g2
Create Date: 2025-11-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1g2h3'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1g2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add discount codes feature.

    Creates discount_codes table to allow event organizers to create discount codes
    for their events. Adds discount tracking fields to registrations table.
    """
    # Create discount_codes table
    op.create_table(
        'discount_codes',
        sa.Column('code_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('discount_type', sa.String(length=20), nullable=False),
        sa.Column('discount_value', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('used_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('code_id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.event_id'], name='fk_discount_codes_event_id', ondelete='CASCADE'),
        sa.UniqueConstraint('event_id', 'code', name='uix_event_code'),
        sa.CheckConstraint("discount_type IN ('percentage', 'fixed_amount')", name='check_discount_type'),
        sa.CheckConstraint("discount_value > 0", name='check_discount_value_positive'),
        sa.CheckConstraint("max_uses IS NULL OR max_uses > 0", name='check_max_uses_positive'),
        sa.CheckConstraint("used_count >= 0", name='check_used_count_non_negative')
    )

    op.create_index('ix_discount_codes_event_id', 'discount_codes', ['event_id'])
    op.create_index('ix_discount_codes_code', 'discount_codes', ['code'])

    # Add discount-related columns to registrations table
    op.add_column('registrations', sa.Column('discount_code_id', sa.Integer(), nullable=True))
    op.add_column('registrations', sa.Column('discount_amount_euros', sa.DECIMAL(precision=10, scale=2), nullable=True))
    op.add_column('registrations', sa.Column('final_amount_euros', sa.DECIMAL(precision=10, scale=2), nullable=True))

    op.create_foreign_key(
        'fk_registrations_discount_code_id',
        'registrations',
        'discount_codes',
        ['discount_code_id'],
        ['code_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Remove discount codes feature."""
    op.drop_constraint('fk_registrations_discount_code_id', 'registrations', type_='foreignkey')
    op.drop_column('registrations', 'final_amount_euros')
    op.drop_column('registrations', 'discount_amount_euros')
    op.drop_column('registrations', 'discount_code_id')

    op.drop_index('ix_discount_codes_code', table_name='discount_codes')
    op.drop_index('ix_discount_codes_event_id', table_name='discount_codes')
    op.drop_table('discount_codes')
