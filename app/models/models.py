from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship, declarative_base
import time

Base = declarative_base()

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    isDeleted = Column(Boolean, default=False)
    messages = relationship("Message", back_populates="chat")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, ForeignKey("chats.chat_id"), nullable=False)  # Fixed: reference chat_id string
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(Integer, default=int(time.time()))
    chat = relationship("Chat", back_populates="messages")

class QueryModel(BaseModel):
    question: str
    model: str
    chat_id: str
    chat_name: str