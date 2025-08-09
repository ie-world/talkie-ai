from fastapi import APIRouter, HTTPException
from app.schemas.learning import LearningRequest, LearningResponse
from app.services.prompt_builder import build_learning_prompts
from app.services.clova_client import call_clova_studio

router = APIRouter()

@router.post("", response_model=LearningResponse)
async def generate_learning_content(request: LearningRequest):
    try:
        messages = build_learning_prompts(request.type)
        result = await call_clova_studio(messages)
        return LearningResponse(result=result.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
