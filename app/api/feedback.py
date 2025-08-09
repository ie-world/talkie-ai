from fastapi import APIRouter, HTTPException
from app.schemas.feedback import FeedbackRequest, FeedbackResponse, FeedbackAnalysis
from app.services.feedback_logic import analyze_feedback
from app.services.prompt_builder import build_feedback_messages
from app.services.clova_client import call_clova_studio

router = APIRouter()


@router.post("", response_model=FeedbackResponse)
async def generate_feedback(req: FeedbackRequest) -> FeedbackResponse:
    """
    발음 평가 결과를 받아, 정확성/속도/공백을 분석하고
    Clova Studio로 피드백 문장을 생성해 반환
    """
    try:
        # 1) 실제 발화 시간(초) 계산
        # - user_duration: 요청에 duration이 있으면 사용, 없으면 usr_graph 기반 계산
        user_duration_sec = req.duration if req.duration is not None else (len(req.usr_graph) / 50.0)
        # - target_duration: 기준 발화 시간은 ref_graph 기반으로 추정
        target_duration_sec = len(req.ref_graph) / 50.0

        # 2) 내부 분석 (정확성/속도/공백)
        analysis_dict = analyze_feedback(
            target_text=req.target_text,
            result_text=req.result_text,
            target_duration_sec=target_duration_sec,
            user_duration_sec=user_duration_sec,
            ref_graph=req.ref_graph,
            usr_graph=req.usr_graph,
        )

        # 3) 프롬프트(messages) 구성
        messages = build_feedback_messages(
            target_text=req.target_text,
            result_text=req.result_text,
            assessment_score=req.assessment_score,
            assessment_details=req.assessment_details,
            wpm_target=analysis_dict["wpm_target"],
            wpm_user=analysis_dict["wpm_user"],
            issue=analysis_dict["issue"],
            accuracy_ok=analysis_dict["accuracy_ok"],
            speed=analysis_dict["speed"],
            gaps=analysis_dict["gaps"],
        )

        # 4) Clova Studio 호출 → 피드백 한 문장 생성
        feedback_text = await call_clova_studio(messages)
        feedback_text = feedback_text.strip().replace("\n", " ")

        # 5) 응답 구성
        analysis = FeedbackAnalysis(**analysis_dict)
        return FeedbackResponse(
            feedback_text=feedback_text,
            analysis=analysis
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
