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
def _issue_instruction(issue: str, speed: str, gaps: bool) -> str:
    """
    이슈 유형에 따라 한 문장 피드백 지시문을 선택
    - 반환 텍스트는 '모델에게 줄 지시'가 아니라 '학습자에게 줄 메시지'의 톤/방향을 설명하는 문장
    """
    if issue == "accuracy":
        return (
            "정확도 문제가 있으니 기준 문장과 다른 단어를 바로잡아 주고, "
            "학습자가 다음에 어떻게 말하면 좋을지 간단한 지침을 한 문장으로 제시하세요."
        )
    if issue == "speed_fast":
        return (
            "속도가 지나치게 빠르니 속도를 약간 늦추도록 권하고, 호흡을 고르고 끊지 않고 자연스럽게 말하라는 조언을 한 문장으로 제시하세요."
        )
    if issue == "speed_slow":
        return (
            "속도가 느리니 약간 빠르게 말하되 한 호흡으로 자연스럽게 이어 말하라는 조언을 한 문장으로 제시하세요."
        )
    if issue == "gaps":
        return (
            "단어 사이 공백이 크니 단어를 붙여서 자연스럽게 이어 말하라고 안내하는 한 문장을 제시하세요."
        )
    # good
    return (
        "전반적으로 발음과 속도가 좋으니 간단히 칭찬하고, 다음에도 같은 리듬으로 이어가라고 격려하는 한 문장을 제시하세요."
    )


def build_feedback_messages(
    *,
    target_text: str,
    result_text: str,
    issue: str,          # "accuracy" | "speed_fast" | "speed_slow" | "gaps" | "good"
    accuracy_ok: bool,
    speed: str,          # "fast" | "slow" | "ok"
    gaps: bool,
    wpm_user: float,     # 분당 단어수
) -> List[dict]:
    
    # 시스템 규칙: 반드시 한 문장, 한국어, 과도한 친절말투/감탄사 남용 금지
    system_content = (
        "너는 성인 한국어 학습자를 위한 간단 피드백 생성기다.\n"
        "지침:\n"
        "1) 한국어로 한 문장만 생성한다. 2) 50자 이내를 권장한다.\n"
        "3) 이모지, 특수문자, 따옴표, 마크다운, 순번, 불릿 사용 금지.\n"
        "4) 장황한 설명, 반복, 사족 금지. 5) 존대하되 단정적으로 짧게.\n"
        "6) 아래 분석 결과를 반영해 가장 중요한 한 가지만 명확히 조언한다."
    )

    # 이슈별 지시
    instruction = _issue_instruction(issue, speed, gaps)

    # 모델이 참고할 컨텍스트
    context = (
        f"[기준 문장] {target_text}\n"
        f"[인식 문장] {result_text}\n"
        f"[판정] issue={issue}, accuracy_ok={accuracy_ok}, speed={speed}, gaps={gaps}, wpm_user={wpm_user:.1f}"
    )

    # 사용자 프롬프트
    user_content = (
        f"{instruction}\n\n"
        f"{context}\n\n"
        "출력 형식: 한국어 한 문장. 조언 핵심만 간결히. 추가 문장, 인용부호, 이모지 금지."
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]