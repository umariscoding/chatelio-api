from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from io import StringIO
import uuid

from app.auth.dependencies import get_current_user, UserContext
from app.services.langchain_service import (
    get_company_rag_chain, 
    stream_company_response,
    setup_company_knowledge_base,
    get_company_vector_store
)
from app.services.fetchdata_service import get_umar_azhar_content
from app.services.document_service import split_text_for_txt
from app.db.database import (
    save_chat, 
    save_message, 
    fetch_messages, 
    fetch_company_chats,
    update_chat_title,
    delete_chat,
    get_company_by_id
)

router = APIRouter(prefix="/chat", tags=["chat"])

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    chat_id: Optional[str] = None
    chat_title: Optional[str] = "New Chat"
    model: str = "Gemini"

class ChatTitleUpdate(BaseModel):
    title: str

class ChatResponse(BaseModel):
    chat_id: str
    message: str
    response: str
    timestamp: int

class ChatList(BaseModel):
    chats: List[Dict[str, Any]]

class ChatHistory(BaseModel):
    messages: List[Dict[str, Any]]

@router.post("/send")
async def send_message(
    message_data: ChatMessage,
    user: UserContext = Depends(get_current_user)
) -> StreamingResponse:
    """
    Send a message to the chatbot and get a streaming response.
    Works for both registered users and guest sessions.
    """
    try:
        # Ensure company knowledge base is set up
        await ensure_company_knowledge_base(user.company_id)
        
        # Generate chat_id if not provided
        chat_id = message_data.chat_id or str(uuid.uuid4())
        
        # Determine user_id and session_id based on user type
        user_id = user.user_id if user.user_type == "user" else None
        session_id = user.user_id if user.user_type == "guest" else None  # For guests, user_id is session_id
        
        # Save chat and human message
        await save_chat(
            company_id=user.company_id,
            chat_id=chat_id,
            title=message_data.chat_title or "New Chat",
            user_id=user_id,
            session_id=session_id
        )
        
        await save_message(
            company_id=user.company_id,
            chat_id=chat_id,
            role="human",
            content=message_data.message
        )
        
        # Set up response buffering for saving
        response_buffer = StringIO()
        
        async def stream_and_save():
            """Stream response and save to database"""
            try:
                # Add chat_id to response headers
                async def generate_response():
                    yield f"data: {{'chat_id': '{chat_id}', 'type': 'start'}}\n\n"
                    
                    async for chunk in stream_company_response(
                        company_id=user.company_id,
                        query=message_data.message,
                        chat_id=chat_id,
                        llm_model=message_data.model
                    ):
                        response_buffer.write(chunk)
                        yield f"data: {{'content': '{chunk.replace(chr(10), ' ').replace(chr(13), ' ')}', 'type': 'chunk'}}\n\n"
                    
                    yield f"data: {{'type': 'end'}}\n\n"
                    
                    # Save complete AI response
                    complete_response = response_buffer.getvalue()
                    await save_message(
                        company_id=user.company_id,
                        chat_id=chat_id,
                        role="ai",
                        content=complete_response
                    )
                
                async for chunk in generate_response():
                    yield chunk
                    
            except Exception as e:
                yield f"data: {{'error': '{str(e)}', 'type': 'error'}}\n\n"
        
        return StreamingResponse(
            stream_and_save(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Chat-ID": chat_id
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.get("/history/{chat_id}")
async def get_chat_history(
    chat_id: str,
    user: UserContext = Depends(get_current_user)
) -> ChatHistory:
    """
    Get chat history for a specific chat.
    Only accessible by users/guests belonging to the same company.
    """
    try:
        # Fetch messages for this company and chat
        messages = await fetch_messages(user.company_id, chat_id)
        
        # Additional access control: verify the chat belongs to this user/session
        chats = await fetch_company_chats(
            company_id=user.company_id,
            user_id=user.user_id if user.user_type == "user" else None,
            session_id=user.user_id if user.user_type == "guest" else None
        )
        
        # Check if this chat belongs to the user
        chat_exists = any(chat["chat_id"] == chat_id for chat in chats)
        if not chat_exists:
            raise HTTPException(status_code=404, detail="Chat not found or access denied")
        
        return ChatHistory(messages=messages)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat history: {str(e)}")

@router.get("/list")
async def list_chats(
    user: UserContext = Depends(get_current_user)
) -> ChatList:
    """
    List all chats for the current user/guest session.
    Only shows chats belonging to the same company.
    """
    try:
        # Determine user_id and session_id based on user type
        user_id = user.user_id if user.user_type == "user" else None
        session_id = user.user_id if user.user_type == "guest" else None
        
        # Fetch chats for this company and user
        chats = await fetch_company_chats(
            company_id=user.company_id,
            user_id=user_id,
            session_id=session_id
        )
        
        return ChatList(chats=chats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chats: {str(e)}")

@router.put("/title/{chat_id}")
async def update_chat_title_endpoint(
    chat_id: str,
    title_data: ChatTitleUpdate,
    user: UserContext = Depends(get_current_user)
):
    """
    Update the title of a chat.
    Only accessible by the owner of the chat.
    """
    try:
        # Verify the chat belongs to this user
        chats = await fetch_company_chats(
            company_id=user.company_id,
            user_id=user.user_id if user.user_type == "user" else None,
            session_id=user.user_id if user.user_type == "guest" else None
        )
        
        chat_exists = any(chat["chat_id"] == chat_id for chat in chats)
        if not chat_exists:
            raise HTTPException(status_code=404, detail="Chat not found or access denied")
        
        # Update the chat title
        await update_chat_title(user.company_id, chat_id, title_data.title)
        
        return {"message": "Chat title updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update chat title: {str(e)}")

@router.delete("/{chat_id}")
async def delete_chat_endpoint(
    chat_id: str,
    user: UserContext = Depends(get_current_user)
):
    """
    Delete a chat.
    Only accessible by the owner of the chat.
    """
    try:
        # Verify the chat belongs to this user
        chats = await fetch_company_chats(
            company_id=user.company_id,
            user_id=user.user_id if user.user_type == "user" else None,
            session_id=user.user_id if user.user_type == "guest" else None
        )
        
        chat_exists = any(chat["chat_id"] == chat_id for chat in chats)
        if not chat_exists:
            raise HTTPException(status_code=404, detail="Chat not found or access denied")
        
        # Delete the chat
        await delete_chat(user.company_id, chat_id)
        
        return {"message": "Chat deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat: {str(e)}")

@router.post("/setup-knowledge-base")
async def setup_knowledge_base(
    user: UserContext = Depends(get_current_user)
):
    """
    Set up the knowledge base for a company.
    Only accessible by company users (not guests).
    """
    try:
        # Only company users can set up knowledge base
        if user.user_type != "company":
            raise HTTPException(status_code=403, detail="Only company users can set up knowledge base")
        
        # For now, use the same dummy data for all companies
        content = get_umar_azhar_content()
        doc_chunks = split_text_for_txt(content)
        
        # Set up company knowledge base
        setup_company_knowledge_base(user.company_id, doc_chunks)
        
        return {"message": "Knowledge base set up successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set up knowledge base: {str(e)}")

@router.get("/company-info")
async def get_company_info(
    user: UserContext = Depends(get_current_user)
):
    """
    Get information about the current company.
    """
    try:
        company = await get_company_by_id(user.company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        return {
            "company": {
                "company_id": company["company_id"],
                "name": company["name"],
                "plan": company["plan"],
                "status": company["status"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch company info: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Health check endpoint for chat service.
    """
    return {"status": "healthy", "service": "chat"}

# Helper functions
async def ensure_company_knowledge_base(company_id: str):
    """
    Ensure knowledge base is set up for a company.
    If not exists, create it with dummy data.
    """
    try:
        # Try to get existing vector store
        vector_store = get_company_vector_store(company_id)
        
        # Test if vector store has any data by attempting a simple search
        retriever = vector_store.as_retriever(search_kwargs={"k": 1})
        docs = retriever.invoke("test query")
        
        # If no documents found, set up knowledge base
        if not docs:
            content = get_umar_azhar_content()
            doc_chunks = split_text_for_txt(content)
            setup_company_knowledge_base(company_id, doc_chunks)
            
    except Exception as e:
        # If any error occurs, set up knowledge base
        content = get_umar_azhar_content()
        doc_chunks = split_text_for_txt(content)
        setup_company_knowledge_base(company_id, doc_chunks) 