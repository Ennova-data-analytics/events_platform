from sqlalchemy.orm import Session
from domain import models 
from sqlalchemy import desc 
from datetime import datetime

def create_chat(db: Session, user_id: str, title: str = "New Chat") -> models.Chat:
    """Create a new chat session"""
    db_chat = models.Chat(
        user_id=user_id,
        title=title
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

def get_chat_by_id(db: Session, chat_id: int, user_id: str) -> models.Chat | None:
    """Get a chat by ID"""
    return db.query(models.Chat).filter(
        models.Chat.id == chat_id,
        models.Chat.user_id == user_id
    ).first()

def get_user_chats(db: Session, user_id: str, skip: int = 0, limit: int = 50) -> list[models.Chat]:
    """Get all messages for a chat"""
    return db.query(models.ChatMessage).filter(
        models.Chat.user_id == user_id
    ).order_by(desc(models.Chat.updated_at)).offset(skip).limit(limit).all()

def get_chat_messages(db: Session, chat_id: int) -> list[models.ChatMessage]:
    """Get all messages for a chat"""
    return db.query(models.ChatMessage).filter(
        models.ChatMessage.chat_id == chat_id
    ).order_by(models.ChatMessage.created_at).all()

def update_chat_title(db: Session, chat_id: int, title: str) -> models.Chat:
    """Update chat title"""
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if chat:
        chat.title = title
        chat.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(chat)
    return chat

def delete_chat(db: Session, chat_id: int) -> bool:
    """Delete a chat and all its messages"""
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if chat:
        db.delete(chat)
        db.commit()
        return True
    return False