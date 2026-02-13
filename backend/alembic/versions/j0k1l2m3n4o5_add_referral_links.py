"""add referral links

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-02-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'j0k1l2m3n4o5'
down_revision = 'i9j0k1l2m3n4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'referral_links',
        sa.Column('link_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('referrer_name', sa.String(255), nullable=False),
        sa.Column('commission_percentage', sa.DECIMAL(5, 2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('link_id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.event_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('code'),
        sa.CheckConstraint('commission_percentage >= 0 AND commission_percentage <= 100', name='check_commission_percentage_range'),
    )
    op.create_index('ix_referral_links_link_id', 'referral_links', ['link_id'])
    op.create_index('ix_referral_links_event_id', 'referral_links', ['event_id'])
    op.create_index('ix_referral_links_code', 'referral_links', ['code'])

    op.add_column('registrations', sa.Column('referral_link_id', sa.Integer(), nullable=True))
    op.create_index('ix_registrations_referral_link_id', 'registrations', ['referral_link_id'])
    op.create_foreign_key(
        'fk_registrations_referral_link_id',
        'registrations', 'referral_links',
        ['referral_link_id'], ['link_id'],
        ondelete='SET NULL'
    )


def downgrade():
    op.drop_constraint('fk_registrations_referral_link_id', 'registrations', type_='foreignkey')
    op.drop_index('ix_registrations_referral_link_id', table_name='registrations')
    op.drop_column('registrations', 'referral_link_id')

    op.drop_index('ix_referral_links_code', table_name='referral_links')
    op.drop_index('ix_referral_links_event_id', table_name='referral_links')
    op.drop_index('ix_referral_links_link_id', table_name='referral_links')
    op.drop_table('referral_links')
