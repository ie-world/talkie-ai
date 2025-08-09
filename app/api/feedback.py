from fastapi import APIRouter, HTTPException
from app.schemas.feedback import FeedbackRequest, FeedbackResponse, FeedbackAnalysis
from app.services.feedback_logic import analyze_feedback_with_segments
from app.services.prompt_builder import build_feedback_messages
from app.services.clova_client import call_clova_studio

router = APIRouter()

@router.post("", response_model=FeedbackResponse)
async def generate_feedback(req: FeedbackRequest) -> FeedbackResponse:
    """
    segments 기반으로 정확도/속도/공백을 분석하고, 짧은 피드백 문장을 생성해 반환.
    """
    try:
        if not req.segments:
            raise HTTPException(status_code=400, detail="segments가 비어 있습니다.")

        # 1) 내부 분석
        analysis_dict = analyze_feedback_with_segments(
            target_text=req.target_text,
            result_text=req.result_text,
            user_segments=[s.model_dump() for s in req.segments],
        )

        # 2) 프롬프트 구성
        messages = build_feedback_messages(
            target_text=req.target_text,
            result_text=req.result_text,
            issue=analysis_dict["issue"],
            accuracy_ok=analysis_dict["accuracy_ok"],
            speed=analysis_dict["speed"],
            gaps=analysis_dict["gaps"],
            wpm_user=analysis_dict["wpm_user"],
        )

        # 3) Clova Studio 호출 → 피드백 문장 생성
        feedback_text = await call_clova_studio(messages)
        feedback_text = feedback_text.strip().replace("\n", " ")

        # 4) 응답 구성
        analysis = FeedbackAnalysis(**analysis_dict)
        return FeedbackResponse(feedback_text=feedback_text, analysis=analysis)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
