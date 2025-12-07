"""add ticket types table

Revision ID: f1g2h3i4j5k6
Revises: e1f2g3h4i5j6
Create Date: 2025-12-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP


# revision identifiers, used by Alembic.
revision = 'f1g2h3i4j5k6'
down_revision = 'e1f2g3h4i5j6'
branch_labels = None
depends_on = None


def upgrade():
    # Create ticket_types table
    op.create_table(
        'ticket_types',
        sa.Column('ticket_type_id', sa.Integer(), primary_key=True, index=True),
        sa.Column('event_id', sa.Integer(), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price_euros', sa.DECIMAL(10, 2), nullable=False, server_default='0.00'),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.Column('tickets_sold', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('form_template_id', sa.Integer(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_free_for_members', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),

        # Foreign keys
        sa.ForeignKeyConstraint(['event_id'], ['events.event_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['form_template_id'], ['form_templates.template_id'], ondelete='SET NULL'),

        # Check constraints
        sa.CheckConstraint('price_euros >= 0', name='check_ticket_price_non_negative'),
        sa.CheckConstraint('capacity IS NULL OR capacity > 0', name='check_ticket_capacity_positive'),
        sa.CheckConstraint('tickets_sold >= 0', name='check_tickets_sold_non_negative'),
        sa.CheckConstraint('display_order >= 0', name='check_display_order_non_negative'),
    )

    # Add ticket_type_id to registrations table
    op.add_column(
        'registrations',
        sa.Column('ticket_type_id', sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        'fk_registrations_ticket_type_id',
        'registrations',
        'ticket_types',
        ['ticket_type_id'],
        ['ticket_type_id'],
        ondelete='SET NULL'
    )

    # Create index on ticket_type_id for faster queries
    op.create_index('ix_registrations_ticket_type_id', 'registrations', ['ticket_type_id'])


def downgrade():
    # Drop index and foreign key from registrations
    op.drop_index('ix_registrations_ticket_type_id', 'registrations')
    op.drop_constraint('fk_registrations_ticket_type_id', 'registrations', type_='foreignkey')
    op.drop_column('registrations', 'ticket_type_id')

    # Drop ticket_types table
    op.drop_table('ticket_types')
