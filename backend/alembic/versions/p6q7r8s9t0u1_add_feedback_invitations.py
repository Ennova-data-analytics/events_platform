"""Add event_feedback_templates join table and feedback_invitations table

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-03-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'p6q7r8s9t0u1'
down_revision: Union[str, None] = 'o5p6q7r8s9t0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- event_feedback_templates join table ---
    op.create_table(
        'event_feedback_templates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.event_id', ondelete='CASCADE'), nullable=False),
        sa.Column('template_id', sa.Integer(), sa.ForeignKey('feedback_templates.template_id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('display_order >= 0', name='check_eft_display_order_non_negative'),
    )
    op.create_index('ix_event_feedback_templates_event_id', 'event_feedback_templates', ['event_id'])
    op.create_index('ix_event_feedback_templates_template_id', 'event_feedback_templates', ['template_id'])

    # Backfill: for every event that already has a feedback_template_id set,
    # insert a row in the join table marked as primary.
    op.execute("""
        INSERT INTO event_feedback_templates (event_id, template_id, is_primary, display_order, created_at)
        SELECT event_id, feedback_template_id, true, 0, now()
        FROM events
        WHERE feedback_template_id IS NOT NULL
    """)

    # --- feedback_invitations table ---
    op.create_table(
        'feedback_invitations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.event_id', ondelete='CASCADE'), nullable=False),
        sa.Column('feedback_template_id', sa.Integer(), sa.ForeignKey('feedback_templates.template_id', ondelete='CASCADE'), nullable=False),
        sa.Column('registration_id', sa.Integer(), sa.ForeignKey('registrations.registration_id', ondelete='CASCADE'), nullable=True),
        sa.Column('external_email', sa.String(255), nullable=True),
        sa.Column('external_name', sa.String(255), nullable=True),
        sa.Column('token', sa.String(128), unique=True, nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('submitted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('resent_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index('ix_feedback_invitations_event_id', 'feedback_invitations', ['event_id'])
    op.create_index('ix_feedback_invitations_template_id', 'feedback_invitations', ['feedback_template_id'])
    op.create_index('ix_feedback_invitations_registration_id', 'feedback_invitations', ['registration_id'])
    op.create_index('ix_feedback_invitations_token', 'feedback_invitations', ['token'], unique=True)


def downgrade() -> None:
    op.drop_table('feedback_invitations')
    op.drop_table('event_feedback_templates')
