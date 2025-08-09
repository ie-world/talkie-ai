from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    topic: str
    user_input: Optional[str] = None
    history: List[Message] = []

class ChatResponse(BaseModel):
    ai_response: str
