from __future__ import annotations
from typing import List, Literal, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

# ===== 내부 구조 =====

class WordItem(BaseModel):
    """단어 타임스탬프 한 항목"""
    start: int = Field(..., description="단어 시작(ms)")
    end: int = Field(..., description="단어 종료(ms)")
    token: str = Field("", description="인식된 토큰(단어)")

class Segment(BaseModel):
    """
    STT 세그먼트
    - words가 [[start,end,"token"], ...] 형태 -> 객체로 변환
    """
    model_config = ConfigDict(extra="ignore")  # text/confidence 등 기타 필드는 무시

    start: int = Field(..., description="세그먼트 시작(ms)")
    end: int = Field(..., description="세그먼트 종료(ms)")
    words: List[WordItem] = Field(default_factory=list, description="단어 단위 타임스탬프")

    @field_validator("words", mode="before")
    @classmethod
    def _coerce_words(cls, v: Any) -> List[WordItem]:
        if v is None:
            return []
        # [[s,e,'tok']] 형태를 WordItem 리스트로 변환
        if isinstance(v, list) and v and isinstance(v[0], list):
            converted = []
            for item in v:
                if len(item) >= 2:
                    s = int(item[0]); e = int(item[1])
                    tok = str(item[2]) if len(item) >= 3 else ""
                    converted.append(WordItem(start=s, end=e, token=tok))
            return converted
        return v

# ===== 요청/응답 =====

SpeedLabel = Literal["fast", "slow", "ok"]
IssueLabel = Literal["accuracy", "speed_fast", "speed_slow", "gaps", "good"]

class FeedbackRequest(BaseModel):
    """
    발음 피드백 요청
    """
    target_text: str = Field(..., description="기준 문장")
    result_text: str = Field(..., description="STT 인식 결과 문장")
    segments: List[Segment] = Field(..., description="사용자 발화 세그먼트")

class FeedbackAnalysis(BaseModel):
    issue: IssueLabel
    accuracy_ok: bool
    speed: SpeedLabel
    gaps: bool
    wpm_user: float

    # 튜닝용 참고 지표
    wer: float
    wps_total: float
    wps_art: float
    pause_ms: int
    longest_pause_ms: int
    total_ms: int
    speech_ms: int
    n_words: int

class FeedbackResponse(BaseModel):
    feedback_text: str
    analysis: FeedbackAnalysis
