import time
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any
from app.models.models import Base, Chat, Message
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from app.core.config import DATABASE_URL

DATABASE_URL = "sqlite:///chat_history.db"

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

async def save_chat(chat_id: str, title: str):
    """
    Saves a new chat to the database or updates existing one.
    
    Args:
        chat_id (str): Unique identifier for the chat
        title (str): Title of the chat
    """
    db = next(get_db())
    try:
        chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
        if not chat:
            chat = Chat(chat_id=chat_id, title=title)
            db.add(chat)
            db.commit()
            db.refresh(chat)
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()

async def save_message(chat_id: str, role: str, content: str):
    """
    Saves a message to the database under specified chat.
    
    Args:
        chat_id (str): ID of the chat the message belongs to
        role (str): Role of the message sender (e.g., 'human', 'ai')
        content (str): Content of the message
    """
    db = next(get_db())
    try:
        chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
        if not chat:
            chat = Chat(chat_id=chat_id, title="New Chat")
            db.add(chat)
            db.commit()
            db.refresh(chat)

        message = Message(chat_id=chat_id, role=role, content=content, timestamp=int(time.time()))
        db.add(message)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()

async def update_chat_title(chat_id: str, new_title: str):
    """
    Updates the title of an existing chat.
    
    Args:
        chat_id (str): ID of the chat to update
        new_title (str): New title for the chat
    """
    db = next(get_db())
    try:
        # Use update statement instead of direct assignment
        db.execute(
            update(Chat).where(Chat.chat_id == chat_id).values(title=new_title)
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()

async def fetch_messages(chat_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all messages for a specific chat.
    
    Args:
        chat_id (str): ID of the chat to fetch messages from
        
    Returns:
        List[Dict[str, Any]]: List of messages with role, content, and timestamp
    """
    db = next(get_db())
    messages = []
    try:
        messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.timestamp).all()
        messages = [{"role": message.role, "content": message.content, "timestamp": message.timestamp} for message in messages]
    except SQLAlchemyError:
        pass
    finally:
        db.close()
    
    return messages

async def fetch_all_chats() -> List[Dict[str, Any]]:
    """
    Retrieves all chats from the database. Creates a default chat if none exist.
    
    Returns:
        List[Dict[str, Any]]: List of chats with chat_id, title, and isDeleted status
    """
    db = next(get_db())
    try:
        chats = db.query(Chat).all()
        if not chats:
            new_chat = Chat(chat_id="default_chat", title="Default Chat", isDeleted=False)
            db.add(new_chat)
            db.commit()
            db.refresh(new_chat)
            result = [{"chat_id": new_chat.chat_id, "title": new_chat.title, "isDeleted": new_chat.isDeleted}]
        else:
            result = [{"chat_id": chat.chat_id, "title": chat.title, "isDeleted": chat.isDeleted} for chat in chats]
    except SQLAlchemyError:
        result = []
    finally:
        db.close()
    
    return result

async def delete_chat(chat_id: str):
    """
    Marks a chat as deleted in the database.
    
    Args:
        chat_id (str): ID of the chat to mark as deleted
    """
    db = next(get_db())
    try:
        # Use update statement instead of direct assignment
        db.execute(
            update(Chat).where(Chat.chat_id == chat_id).values(isDeleted=True)
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()

async def delete_all_chats():
    """
    Marks all chats as deleted in the database.
    """
    db = next(get_db())
    try:
        # Use update statement for all chats
        db.execute(update(Chat).values(isDeleted=True))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()

def load_session_history(chat_id: str) -> ChatMessageHistory:
    """
    Loads chat history for a specific chat and converts it to ChatMessageHistory format.
    
    Args:
        chat_id (str): ID of the chat to load history from
        
    Returns:
        ChatMessageHistory: Object containing the chat's message history
    """
    db = next(get_db())
    chat_history = ChatMessageHistory()
    
    try:
        # Query messages directly, ordered by timestamp
        messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.timestamp).all()
        
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
