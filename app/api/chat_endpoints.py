from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from io import StringIO
import uuid

from app.auth.dependencies import get_current_user, get_current_company, UserContext
from app.services.langchain_service import (
    get_company_rag_chain, 
    stream_company_response,
    setup_company_knowledge_base,
    get_company_vector_store,
    process_company_document,
    clear_company_knowledge_base
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
    get_company_by_id,
    get_or_create_knowledge_base,
    save_document,
    get_company_documents,
    get_document_content,
    delete_document
)

router = APIRouter(prefix="/chat", tags=["chat"])

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    chat_id: Optional[str] = None
    chat_title: Optional[str] = "New Chat"
    model: str = "OpenAI"

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

class DocumentUpload(BaseModel):
    content: str
    filename: str = "document.txt"

class DocumentList(BaseModel):
    documents: List[Dict[str, Any]]

class KnowledgeBaseInfo(BaseModel):
    kb_id: str
    name: str
    description: str
    status: str
    file_count: int
    created_at: Any
    updated_at: Any

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

@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    user: UserContext = Depends(get_current_company)
):
    """
    Upload a text document to the company's knowledge base.
    Only accessible by company users.
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('text/'):
            raise HTTPException(
                status_code=400, 
                detail="Only text files are supported"
            )
        
        # Validate file size (max 10MB)
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=400,
                detail="File size too large. Maximum 10MB allowed."
            )
        
        # Decode content
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="File must be valid UTF-8 text"
            )
        
        # Get or create knowledge base
        kb = await get_or_create_knowledge_base(user.company_id)
        
        # Save document to database
        document = await save_document(
            kb_id=kb["kb_id"],
            filename=file.filename or "document.txt",
            content=text_content,
            content_type=file.content_type or "text/plain"
        )
        
        # Process document in background
        success = process_company_document(
            company_id=user.company_id,
            document_content=text_content,
            doc_id=document["doc_id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to process document"
            )
        
        return {
            "message": "Document uploaded and processed successfully",
            "document": document,
            "knowledge_base": kb
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload document: {str(e)}"
        )

@router.post("/upload-text")
async def upload_text_content(
    document_data: DocumentUpload,
    user: UserContext = Depends(get_current_company)
):
    """
    Upload text content directly to the company's knowledge base.
    Only accessible by company users.
    """
    try:
        # Validate content size (max 10MB)
        if len(document_data.content.encode('utf-8')) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Content size too large. Maximum 10MB allowed."
            )
        
        # Get or create knowledge base
        kb = await get_or_create_knowledge_base(user.company_id)
        
        # Save document to database
        document = await save_document(
            kb_id=kb["kb_id"],
            filename=document_data.filename,
            content=document_data.content,
            content_type="text/plain"
        )
        
        # Process document
        success = process_company_document(
            company_id=user.company_id,
            document_content=document_data.content,
            doc_id=document["doc_id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to process document"
            )
        
        return {
            "message": "Text content uploaded and processed successfully",
            "document": document,
            "knowledge_base": kb
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload text content: {str(e)}"
        )

@router.get("/documents")
async def list_documents(
    user: UserContext = Depends(get_current_company)
) -> DocumentList:
    """
    List all documents in the company's knowledge base.
    Only accessible by company users.
    """
    try:
        documents = await get_company_documents(user.company_id)
        return DocumentList(documents=documents)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch documents: {str(e)}"
        )

@router.get("/knowledge-base")
async def get_knowledge_base_info(
    user: UserContext = Depends(get_current_company)
) -> KnowledgeBaseInfo:
    """
    Get knowledge base information for the company.
    Only accessible by company users.
    """
    try:
        kb = await get_or_create_knowledge_base(user.company_id)
        return KnowledgeBaseInfo(**kb)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch knowledge base info: {str(e)}"
        )

@router.delete("/documents/{doc_id}")
async def delete_document_endpoint(
    doc_id: str,
    user: UserContext = Depends(get_current_company)
):
    """
    Delete a document from the company's knowledge base.
    Only accessible by company users.
    """
    try:
        success = await delete_document(doc_id, user.company_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )

@router.post("/clear-knowledge-base")
async def clear_knowledge_base(
    user: UserContext = Depends(get_current_company)
):
    """
    Clear all content from the company's knowledge base.
    Only accessible by company users.
    """
    try:
        success = clear_company_knowledge_base(user.company_id)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to clear knowledge base"
            )
        
        return {"message": "Knowledge base cleared successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear knowledge base: {str(e)}"
        )

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