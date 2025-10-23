"""add_feedback_templates

Revision ID: 57891b0ac72c
Revises: f5c85b6bb780
Create Date: 2025-10-22 20:35:00.168281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision: str = '57891b0ac72c'
down_revision: Union[str, Sequence[str], None] = 'f5c85b6bb780'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create feedback_templates table
    op.create_table(
        'feedback_templates',
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('template_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('fields', JSONB(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('template_id')
    )

    # Add feedback_template_id to events table
    op.add_column('events',
        sa.Column('feedback_template_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_events_feedback_template',
        'events', 'feedback_templates',
        ['feedback_template_id'], ['template_id'],
        ondelete='SET NULL'
    )

    # Modify feedback table - backup existing data first if needed
    # Drop old columns
    op.drop_column('feedback', 'respondent_type')
    op.drop_column('feedback', 'satisfaction_score')
    op.drop_column('feedback', 'comments')

    # Add new columns
    op.add_column('feedback',
        sa.Column('feedback_template_id', sa.Integer(), nullable=True)
    )
    op.add_column('feedback',
        sa.Column('form_responses', JSONB(), nullable=True)
    )
    op.add_column('feedback',
        sa.Column('is_anonymous', sa.Boolean(), nullable=False, server_default='false')
    )

    # Add foreign key for feedback_template_id
    op.create_foreign_key(
        'fk_feedback_template',
        'feedback', 'feedback_templates',
        ['feedback_template_id'], ['template_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign key and column from feedback
    op.drop_constraint('fk_feedback_template', 'feedback', type_='foreignkey')
    op.drop_column('feedback', 'is_anonymous')
    op.drop_column('feedback', 'form_responses')
    op.drop_column('feedback', 'feedback_template_id')

    # Restore old columns
    op.add_column('feedback',
        sa.Column('respondent_type', sa.String(length=50), nullable=False)
    )
    op.add_column('feedback',
        sa.Column('satisfaction_score', sa.Integer(), nullable=True)
    )
    op.add_column('feedback',
        sa.Column('comments', sa.Text(), nullable=True)
    )

    # Remove feedback_template_id from events
    op.drop_constraint('fk_events_feedback_template', 'events', type_='foreignkey')
    op.drop_column('events', 'feedback_template_id')

    # Drop feedback_templates table
    op.drop_table('feedback_templates')
