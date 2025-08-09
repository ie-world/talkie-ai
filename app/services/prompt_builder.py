from app.constants.topics import TOPIC_PROMPTS
from typing import List, Dict

# 단어, 문장 생성용 프롬프트
def build_learning_prompts(request_type: str) -> list[dict]:
    if request_type == "word":
        return [
            {
                "role": "system",
                "content": (
                    "너는 성인의 한국어 학습을 위한 단어 생성기야.\n\n"
                    "조건은 다음과 같아:\n\n"
                    "1. 일상생활에서 자주 사용하는, 쉬운 한국어 단어 '1개만' 출력해야 해.\n"
                    "2. 출력은 오직 단어 '하나'만, 설명 없이. 예: 떡볶이\n"
                    "3. 음식, 운동, 음악, 여행, 날씨, 동물, 영화/드라마, 책, 물건, 회의, 병원, 대중교통 등 주제 안에서 랜덤으로 단어 1개만 선택해.\n"
                    "4. 절대 설명하지 마. 추가 문장, 부연설명, 예시, 포맷팅, 강조표현 사용 금지.\n"
                    "5. 딱 하나의 단어만 줄 바꿈 없이 출력해. 예: 버스\n\n"
                    "지시를 어기면 학습자가 헷갈릴 수 있어. 무조건 단어 하나만 출력해."
                )
            },
            {
                "role": "user",
                "content": "단어 생성"
            }
        ]
    
    elif request_type == "sentence":
        return [
            {
                "role": "system",
                "content": (
                    "너는 성인의 한국어 학습을 위한 문장 생성기야.\n\n"
                    "조건은 다음과 같아:\n\n"
                    "1. 일상생활에서 자주 사용하는, 짧은 한국어 문장을 출력해야 해.\n"
                    "2. 출력은 오직 문장 '하나'만, 설명 없이.\n"
                    "3. 음식, 운동, 음악, 여행, 날씨, 동물, 영화/드라마, 책, 물건, 회의, 병원, 대중교통 등 주제 안에서 랜덤으로 문장 1개만 선택해.\n"
                    "4. 절대 설명하지 마. 추가 문장, 부연설명, 예시, 포맷팅, 강조표현 사용 금지.\n"
                    "5. 딱 하나의 문장만 줄 바꿈 없이 출력해.\n\n"
                    "지시를 어기면 학습자가 헷갈릴 수 있어. 무조건 짧은 문장 하나만 출력해."
                )
            },
            {
                "role": "user",
                "content": "문장 생성"
            }
        ]
    else:
        raise ValueError("Invalid request type")



# 자유 대화용 프롬프트
def build_chat_prompt(topic: str, history: list[dict], user_input: str | None) -> list[dict]:
    if topic not in TOPIC_PROMPTS:
        raise ValueError(f"Unknown topic: {topic}")
    
    system_message = {"role": "system", "content": TOPIC_PROMPTS[topic]}
    messages = [system_message]

    # 이전 대화 히스토리 추가
    messages.extend(history)

    # user_input이 있다면 추가
    if user_input is not None:
        messages.append({"role": "user", "content": user_input})
    else:
        # 대화 시작 상황
        messages.append({"role": "user", "content": "대화 시작"})

    return messages



# 피드백 생성용 프롬프트
def build_feedback_messages(
    *,
    target_text: str,
    result_text: str,
    assessment_score: int,
    assessment_details: str,
    wpm_target: float,
    wpm_user: float,
    issue: str,               # 'accuracy' | 'speed_fast' | 'speed_slow' | 'gaps' | 'good'
    accuracy_ok: bool,
    speed: str,               # 'fast' | 'slow' | 'ok'
    gaps: bool
) -> List[Dict]:

    system = {
        "role": "system",
        "content": (
            "너는 성인의 한국어 발음 학습을 돕는 코치야.\n"
            "입력으로 발음 평가 결과와 분석 요약이 주어지면, 학습자에게 도움이 되는 '짧은 한국어 피드백'을 1문장만 생성해.\n"
            "규칙:\n"
            "1) 친절하고 격려하는 말투를 사용해.\n"
            "2) 출력은 '문장 하나'만, 불필요한 설명/목록/불릿/이모지/강조 금지.\n"
            "3) 가능한 한 구체적이고 실행 가능한 조언을 1개만 담아.\n"
            "4) 너무 기술적인 용어는 피하고, 쉬운 단어를 사용해.\n"
            "5) 맞춤법과 띄어쓰기를 정확히 지켜.\n"
            "6) 아래 이슈 유형별 코칭 가이드를 우선 적용해:\n"
            "   - accuracy: 정답 문장과 달랐다면, 출력은 '정확하게 말해볼까요?' 로만 답해. 다른 말은 붙이지 마.\n"
            "   - speed_fast: 속도가 빨랐다면, 한 단어씩 끊지 말고 호흡을 고르며 천천히 말하도록 유도.\n"
            "   - speed_slow: 속도가 느리다면, 끊기는 부분을 줄이고 한 호흡에 자연스럽게 이어 말하도록 유도.\n"
            "   - gaps: 불필요한 공백이 있었다면, 단어 사이 간격을 줄이고 자연스럽게 '붙여서' 말하도록 유도.\n"
            "   - good: 전반적으로 좋다면, 잘한 점을 짧게 칭찬하고 유지하도록 안내.\n"
        )
    }

    # 모델이 상황을 정확히 파악하도록 구조화된 사실 정보를 user에 전달
    user = {
        "role": "user",
        "content": (
            f"[기준 문장] {target_text}\n"
            f"[인식 문장] {result_text}\n"
            f"[총점] {assessment_score}\n"
            f"[단어별 점수(원문)] {assessment_details}\n"
            f"[WPM] target={wpm_target}, user={wpm_user}\n"
            f"[판정] issue={issue}, accuracy_ok={accuracy_ok}, speed={speed}, gaps={gaps}\n"
            "위 정보를 바탕으로 학습자에게 도움 되는 짧은 한국어 피드백 '문장 하나'만 만들어줘."
        )
    }

    return [system, user]