"""add_email_templates_table

Revision ID: c2e9b6aee84a
Revises: 1a4e1ff0b818
Create Date: 2025-10-21 08:29:05.602153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2e9b6aee84a'
down_revision: Union[str, Sequence[str], None] = '1a4e1ff0b818'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create email_templates table
    op.create_table(
        'email_templates',
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('template_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('template_type', sa.String(length=50), nullable=False),
        sa.Column('html_content', sa.Text(), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('subject_template', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('template_id')
    )

    # Add email_template_id column to events table
    op.add_column('events', sa.Column('email_template_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_events_email_template_id',
        'events', 'email_templates',
        ['email_template_id'], ['template_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign key and column from events table
    op.drop_constraint('fk_events_email_template_id', 'events', type_='foreignkey')
    op.drop_column('events', 'email_template_id')

    # Drop email_templates table
    op.drop_table('email_templates')
