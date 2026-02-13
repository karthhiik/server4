from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"

class MessageStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"

class MessageMetadata(BaseModel):
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[str] = None
    duration: Optional[str] = None

class MessageCreate(BaseModel):
    recipient_id: str
    content: str
    type: MessageType = MessageType.TEXT
    metadata: Optional[MessageMetadata] = None
    reply_to: Optional[str] = None

class Message(BaseModel):
    id: str = Field(..., alias="_id")
    conversation_id: str
    sender_id: str
    content: str
    type: MessageType
    metadata: Optional[MessageMetadata] = None
    reply_to: Optional[str] = None
    status: MessageStatus
    timestamp: datetime
    
    class Config:
        populate_by_name = True

class Conversation(BaseModel):
    id: str = Field(..., alias="_id")
    participants: List[str]
    last_message: Optional[dict] = None
    updated_at: datetime
    
    class Config:
        populate_by_name = True
