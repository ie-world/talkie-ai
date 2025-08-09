from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


# ====== Request ======
class FeedbackRequest(BaseModel):
    """
    발음 평가 결과를 받아 AI 피드백 생성을 요청하는 바디
    """
    target_text: str = Field(..., description="학습자가 읽어야 하는 기준 문장")
    result_text: str = Field(..., description="STT 결과(Clova Speech API 인식 텍스트)")
    
    duration: Optional[float] = Field(
        None, ge=0, description="실제 녹음 길이(초), 없으면 usr_graph 길이로 계산..."
    )

    assessment_score: int = Field(..., ge=1, le=100, description="문장 전체 발음 점수 (1~100)")
    assessment_details: str = Field(..., description="매 단어마다의 평가 점수")
    ref_graph: List[int] = Field(..., description="기준 발음 파형 그래프(Hz=50)")
    usr_graph: List[int] = Field(..., description="사용자 발음 파형 그래프(Hz=50)")

    @field_validator("ref_graph", "usr_graph")
    @classmethod
    def graphs_must_be_positive(cls, v: List[int]):
        if any(x < 0 for x in v):
            raise ValueError("그래프 수치(ref_graph, usr_graph)는 모두 양의 정수여야 합니다.")
        return v

    @field_validator("duration")
    @classmethod
    def duration_nonnegative(cls, v: Optional[float]):
        if v is not None and v < 0:
            raise ValueError("duration은 0 이상이어야 합니다.")
        return v


# ====== Response ======
class FeedbackAnalysis(BaseModel):
    """
    내부 판단 결과(정확성/속도/공백)와 보조 지표를 함께 반환
    """
    issue: Literal["accuracy", "speed_fast", "speed_slow", "gaps", "good"] = Field(
        ..., description="주된 이슈 유형"
    )
    accuracy_ok: bool = Field(..., description="정확성 통과 여부")
    speed: Literal["fast", "slow", "ok"] = Field(..., description="속도 판정")
    gaps: bool = Field(..., description="파형 공백 이슈 여부")
    wpm_target: Optional[float] = Field(None, description="기준 문장 추정 WPM")
    wpm_user: Optional[float] = Field(None, description="사용자 발화 WPM")


class FeedbackResponse(BaseModel):
    """
    최종 사용자 노출용 피드백 문구 + 내부 분석 리포트
    """
    feedback_text: str = Field(..., description="AI가 생성한 피드백 문장")
    analysis: FeedbackAnalysis