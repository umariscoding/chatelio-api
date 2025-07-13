import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any, Optional
from app.models.models import (
    Base, Company, CompanyUser, GuestSession, KnowledgeBase, 
    Document, Chat, Message
)
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from app.core.config import DATABASE_URL
import bcrypt

# Create new database for multi-tenant setup
DATABASE_URL = "sqlite:///multi_tenant_chat.db"

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    """
    Creates and yields a database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# =============================================================================
# COMPANY MANAGEMENT
# =============================================================================

async def create_company(name: str, email: str, password: str) -> Dict[str, Any]:
    """
    Create a new company account.
    
    Args:
        name: Company name
        email: Company email
        password: Company password
        
    Returns:
        dict: Company information
    """
    db = next(get_db())
    try:
        # Check if company already exists
        existing = db.query(Company).filter(Company.email == email).first()
        if existing:
            raise ValueError("Company with this email already exists")
        
        # Create new company
        company = Company(
            name=name,
            email=email,
            password_hash=hash_password(password)
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        
        return {
            "company_id": company.company_id,
            "name": company.name,
            "email": company.email,
            "plan": company.plan,
            "status": company.status,
            "created_at": company.created_at.isoformat()
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise e
    finally:
        db.close()

async def authenticate_company(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a company and return company info.
    
    Args:
        email: Company email
        password: Company password
        
    Returns:
        dict: Company information if authenticated, None otherwise
    """
    db = next(get_db())
    try:
        company = db.query(Company).filter(Company.email == email).first()
        if company and verify_password(password, str(company.password_hash)):
            return {
                "company_id": company.company_id,
                "name": company.name,
                "email": company.email,
                "plan": company.plan,
                "status": company.status
            }
        return None
    except SQLAlchemyError:
        return None
    finally:
        db.close()

async def get_company_by_id(company_id: str) -> Optional[Dict[str, Any]]:
    """Get company information by ID."""
    db = next(get_db())
    try:
        company = db.query(Company).filter(Company.company_id == company_id).first()
        if company:
            return {
                "company_id": company.company_id,
                "name": company.name,
                "email": company.email,
                "plan": company.plan,
                "status": company.status,
                "settings": company.settings
            }
        return None
    except SQLAlchemyError:
        return None
    finally:
        db.close()

# =============================================================================
# USER MANAGEMENT
# =============================================================================

async def create_user(company_id: str, email: str, name: str) -> Dict[str, Any]:
    """Create a new user for a company."""
    db = next(get_db())
    try:
        user = CompanyUser(
            company_id=company_id,
            email=email,
            name=name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return {
            "user_id": user.user_id,
            "company_id": user.company_id,
            "email": user.email,
            "name": user.name,
            "is_anonymous": user.is_anonymous,
            "created_at": user.created_at.isoformat()
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise e
    finally:
        db.close()

async def create_guest_session(company_id: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, Any]:
    """Create a new guest session."""
    db = next(get_db())
    try:
        expires_at = datetime.now() + timedelta(hours=24)  # 24 hour session
        
        session = GuestSession(
            company_id=company_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return {
            "session_id": session.session_id,
            "company_id": session.company_id,
            "expires_at": session.expires_at.isoformat(),
            "created_at": session.created_at.isoformat()
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise e
    finally:
        db.close()

async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user information by ID."""
    db = next(get_db())
    try:
        user = db.query(CompanyUser).filter(CompanyUser.user_id == user_id).first()
        if user:
            return {
                "user_id": user.user_id,
                "company_id": user.company_id,
                "email": user.email,
                "name": user.name,
                "is_anonymous": user.is_anonymous
            }
        return None
    except SQLAlchemyError:
        return None
    finally:
        db.close()

async def get_guest_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get guest session information."""
    db = next(get_db())
    try:
        session = db.query(GuestSession).filter(GuestSession.session_id == session_id).first()
        if session is not None and session.expires_at.replace(tzinfo=None) > datetime.now():
            return {
                "session_id": session.session_id,
                "company_id": session.company_id,
                "expires_at": session.expires_at.isoformat()
            }
        return None
    except SQLAlchemyError:
        return None
    finally:
        db.close()

# =============================================================================
# CHAT MANAGEMENT (COMPANY-SCOPED)
# =============================================================================

async def save_chat(company_id: str, chat_id: str, title: str, user_id: Optional[str] = None, session_id: Optional[str] = None):
    """
    Save a chat for a specific company.
    
    Args:
        company_id: Company ID
        chat_id: Chat ID
        title: Chat title
        user_id: User ID (for registered users)
        session_id: Session ID (for guest users)
    """
    db = next(get_db())
    try:
        # Check if chat already exists
        chat = db.query(Chat).filter(Chat.chat_id == chat_id, Chat.company_id == company_id).first()
        if not chat:
            chat = Chat(
                chat_id=chat_id,
                company_id=company_id,
                title=title,
                user_id=user_id,
                session_id=session_id,
                is_guest=(session_id is not None)
            )
            db.add(chat)
            db.commit()
            db.refresh(chat)
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()

async def save_message(company_id: str, chat_id: str, role: str, content: str):
    """Save a message for a specific company's chat."""
    db = next(get_db())
    try:
        # Ensure chat exists
        chat = db.query(Chat).filter(Chat.chat_id == chat_id, Chat.company_id == company_id).first()
        if not chat:
            chat = Chat(
                chat_id=chat_id,
                company_id=company_id,
                title="New Chat",
                is_guest=True
            )
            db.add(chat)
            db.commit()
            db.refresh(chat)

        message = Message(
            chat_id=chat_id,
            company_id=company_id,
            role=role,
            content=content,
            timestamp=int(time.time())
        )
        db.add(message)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()

async def fetch_messages(company_id: str, chat_id: str) -> List[Dict[str, Any]]:
    """Fetch all messages for a specific chat in a company."""
    db = next(get_db())
    messages = []
    try:
        messages = db.query(Message).filter(
            Message.chat_id == chat_id,
            Message.company_id == company_id
        ).order_by(Message.timestamp).all()
        
        messages = [
            {
                "role": message.role,
                "content": message.content,
                "timestamp": message.timestamp
            } for message in messages
        ]
    except SQLAlchemyError:
        pass
    finally:
        db.close()
    
    return messages

async def fetch_company_chats(company_id: str, user_id: Optional[str] = None, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch all chats for a company, optionally filtered by user or session."""
    db = next(get_db())
    try:
        query = db.query(Chat).filter(
            Chat.company_id == company_id,
            Chat.is_deleted == False
        )
        
        if user_id:
            query = query.filter(Chat.user_id == user_id)
        elif session_id:
            query = query.filter(Chat.session_id == session_id)
            
        chats = query.all()
        
        if not chats:
            # Create default chat for the company
            default_chat = Chat(
                company_id=company_id,
                title="Default Chat",
                user_id=user_id,
                session_id=session_id,
                is_guest=(session_id is not None)
            )
            db.add(default_chat)
            db.commit()
            db.refresh(default_chat)
            
            result = [{
                "chat_id": default_chat.chat_id,
                "title": default_chat.title,
                "is_guest": default_chat.is_guest,
                "is_deleted": default_chat.is_deleted,
                "created_at": default_chat.created_at.isoformat()
            }]
        else:
            result = [
                {
                    "chat_id": chat.chat_id,
                    "title": chat.title,
                    "is_guest": chat.is_guest,
                    "is_deleted": chat.is_deleted,
                    "created_at": chat.created_at.isoformat()
                } for chat in chats
            ]
    except SQLAlchemyError:
        result = []
    finally:
        db.close()
    
    return result

async def update_chat_title(company_id: str, chat_id: str, new_title: str):
    """Update chat title for a specific company."""
    db = next(get_db())
    try:
        db.execute(
            update(Chat).where(
                Chat.chat_id == chat_id,
                Chat.company_id == company_id
            ).values(title=new_title)
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()

async def delete_chat(company_id: str, chat_id: str):
    """Delete a chat for a specific company."""
    db = next(get_db())
    try:
        db.execute(
            update(Chat).where(
                Chat.chat_id == chat_id,
                Chat.company_id == company_id
            ).values(is_deleted=True)
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()

async def delete_all_chats(company_id: str):
    """Delete all chats for a specific company."""
    db = next(get_db())
    try:
        db.execute(
            update(Chat).where(
                Chat.company_id == company_id
            ).values(is_deleted=True)
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()

def load_session_history(company_id: str, chat_id: str) -> ChatMessageHistory:
    """
    Load chat history for a specific chat in a company.
    
    Args:
        company_id: Company ID
        chat_id: Chat ID
        
    Returns:
        ChatMessageHistory: Object containing the chat's message history
    """
    db = next(get_db())
    chat_history = ChatMessageHistory()
    
    try:
        # Query messages with company scoping
        messages = db.query(Message).filter(
            Message.chat_id == chat_id,
            Message.company_id == company_id
        ).order_by(Message.timestamp).all()
        
        # Add messages to chat history in correct format
        for message in messages:
            role = str(message.role)
            content = str(message.content)
            if role == "human":
                chat_history.add_user_message(content)
            elif role == "ai":
                chat_history.add_ai_message(content)
                
    except SQLAlchemyError as e:
        print(f"Error loading session history: {e}")
    finally:
        db.close()
    
    return chat_history
