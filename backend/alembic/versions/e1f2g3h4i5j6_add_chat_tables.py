"""add chat tables

Revision ID: e1f2g3h4i5j6
Revises: e0f1g2h3i4j5
Create Date: 2025-11-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP


# revision identifiers, used by Alembic.
revision: str = 'e1f2g3h4i5j6'
down_revision: Union[str, Sequence[str], None] = 'e0f1g2h3i4j5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add chat and chat_messages tables for RAG chatbot feature.

    Creates:
    - chats table: Stores chat sessions for users
    - chat_messages table: Stores individual messages within chats
    - message_role enum: Defines message roles (user, assistant, system)
    """

    # Create message_role enum if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create chats table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            title VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # Create indexes if they don't exist
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_chats_id ON chats(id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_chats_user_id ON chats(user_id)
    """)

    # Create chat_messages table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id SERIAL PRIMARY KEY,
            chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
            role message_role NOT NULL,
            content TEXT NOT NULL,
            retrieved_chunks JSON,
            tokens_used INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # Create indexes if they don't exist
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_chat_messages_id ON chat_messages(id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_chat_messages_chat_id ON chat_messages(chat_id)
    """)


def downgrade() -> None:
    """Remove chat tables and enum."""
    op.drop_index(op.f('ix_chat_messages_chat_id'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_id'), table_name='chat_messages')
    op.drop_table('chat_messages')

    op.drop_index(op.f('ix_chats_user_id'), table_name='chats')
    op.drop_index(op.f('ix_chats_id'), table_name='chats')
    op.drop_table('chats')

    # Only drop enum if no other tables are using it
    op.execute("DROP TYPE IF EXISTS message_role CASCADE")
