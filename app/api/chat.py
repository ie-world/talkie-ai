from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.prompt_builder import build_chat_prompt
from app.services.clova_client import call_clova_chat

router = APIRouter()

@router.post("", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    try:
        history = [
            msg.model_dump()
            for msg in request.history
        ]
        messages = build_chat_prompt(
            topic=request.topic,
            history=history,
            user_input=request.user_input
        )
        ai_response = await call_clova_chat(messages)
        return ChatResponse(ai_response=ai_response.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
