from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from api import deps 
from domain import schemas, models
from domain.use_cases import db_chat
from domain.services.ai.chat_service import ChatService
from domain.services.ai.document_vectorization_service import DocumentVectorizationService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=schemas.ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(chat_data: schemas.ChatCreate, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user), chat_service: ChatService = Depends(deps.get_chat_service)):
    """Create a new chat session"""
    try:
        title = "New Chat"
        if chat_data.first_message:
            title = await chat_service.create_chat_title(chat_data.first_message)
        
        new_chat = db_chat.create_chat(db, user_id=current_user.user_id, title=title)

        return schemas.ChatResponse(
            id=new_chat.id,
            title=new_chat.title,
            created_at=new_chat.created_at,
            updated_at=new_chat.updated_at,
            message_count=0
        )
    
    except Exception as e:
        logger.error(f"Error creating chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat"
        )


@router.get("/", response_model=list[schemas.ChatResponse])
async def list_chats(skip: int = 0, limit: int = 50, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    """List all chats for the current user"""
    try:
        chats = db_chat.get_user_chats(db, user_id=current_user.user_id, skip=skip, limit=limit)

        result = []
        for chat in chats:
            messages = db_chat.get_chat_messages(db, chat_id=chat.id)
            last_msg = messages[-1].content[:100] if messages else None

            result.append(schemas.ChatResponse(
                id=chat.id,
                title=chat.title,
                created_at=chat.created_at,
                updated_at=chat.updated_at,
                message_count=len(messages),
                last_message=last_msg
            ))
        
        return result 
    
    except Exception as e:
        logger.error(f"Error listing chats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chats"
        )

@router.get("/{chat_id}", response_model=schemas.ChatDetailResponse)
async def get_chat(chat_id: int, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Get a specific chat with all messages"""
    chat = db_chat.get_chat_by_id(db, chat_id=chat_id, user_id=current_user.user_id)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    messages = db_chat.get_chat_messages(db, chat_id=chat_id)

    return schemas.ChatDetailResponse(
        id=chat.id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=len(messages),
        messages=[schemas.MessageResponse.from_orm(msg) for msg in messages]
    )

@router.post("/{chat_id}/messages")
async def send_message(chat_id: int, message: schemas.MessageCreate, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user), chat_service: ChatService = Depends(deps.get_chat_service), _rate_limit: None = Depends(deps.rate_limit_chat)):
    """Send a message and get streaming response"""
    chat = db_chat.get_chat_by_id(db, chat_id=chat_id, user_id=current_user.user_id)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    messages = db_chat.get_chat_messages(db, chat_id=chat_id)
    chat_history = [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]

    async def generate():
        try:
            async for chunk in chat_service.generate_response(
                user_message=message.content,
                chat_id=chat_id,
                chat_history=chat_history,
                db_session=db
            ):
                yield chunk 
        
        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            yield "Error generating response"
    
    return StreamingResponse(generate(), media_type="text/plain")

@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_endpoint(chat_id: int, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Delete a chat and all its messages"""
    chat = db_chat.get_chat_by_id(db, chat_id=chat_id, user_id=current_user.user_id)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    try:
        db_chat.delete_chat(db, chat_id=chat_id)
    except Exception as e:
        logger.error(f"Error deleting chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat"
        )

@router.patch("/{chat_id}/title", response_model=schemas.ChatResponse)
async def update_chat_title_endpoint(chat_id: int, title_update: schemas.ChatTitleUpdate, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Update chat title"""
    chat = db_chat.get_chat_by_id(db, chat_id=chat_id, user_id=current_user.user_id)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    try:
        updated_chat = db_chat.update_chat_title(db, chat_id=chat_id, title=title_update.title)
        messages = db_chat.get_chat_messages(db, chat_id=chat_id)
        
        return schemas.ChatResponse(
            id=updated_chat.id,
            title=updated_chat.created_at,
            created_at=updated_chat.created_at,
            updated_at=updated_chat.updated_at,
            message_count=len(messages)
        )
    
    except Exception as e:
        logger.error(f"Error updating file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update title"
        )

@router.post("/documents/vectorize", response_model=schemas.DocumentVectorizeResponse)
async def vectorize_document(file: UploadFile = File(...), event_id: int = None, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user), vectorization_service: DocumentVectorizationService = Depends(deps.get_document_vectorization_service)):
    """Upload and vectorize document"""
    if not file.filename.endswith('.docx'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .docx files are supported"
        )
    
    try:
        chunks_count = await vectorization_service.process_document(
            file=file.file,
            filename=file.filename,
            event_id=event_id,
            metadata={
                "uploaded_by": str(current_user.user_id),
                "uploaded_by_email": current_user.email
            }
        )

        return schemas.DocumentVectorizeResponse(
            filename=file.filename,
            chunks_processed=chunks_count,
            event_id=event_id,
            message=f"Successfully vectorized {chunks_count} chunks from {file.filename}"
        )
    
    except Exception as e:
        logger.error(f"Error vectorizing document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to vectorize document"
        )
