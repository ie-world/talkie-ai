import re
from typing import Tuple

# 공백 정리: 여러 공백 → 1칸, 앞뒤 공백 제거
_WS_RE = re.compile(r"\s+")

# 문장에 섞인 일반적인 문장부호 제거용
_PUNCT_RE = re.compile(r"[\"'“”‘’`~!@#$%^&*()\-_=+\[\]{}\\|;:,.<>/?·…]+")


def normalize(text: str) -> str:
    """
    문장에서 문장부호를 제거하고 공백을 정규화
    """
    if not text:
        return ""
    t = _PUNCT_RE.sub(" ", text)
    t = _WS_RE.sub(" ", t).strip()
    return t


def count_words(text: str) -> int:
    """
    띄어쓰기 기준 단어 개수
    """
    t = normalize(text)
    if not t:
        return 0
    return len(t.split(" "))


def wpm(text: str, duration_sec: float, *, min_sec: float = 0.3) -> float:
    """
    WPM(단어/분) = 단어수 / (발화시간(초)/60)
    duration_sec가 너무 작으면 min_sec로 보정해 0/0 방지
    """
    if duration_sec is None or duration_sec <= 0:
        duration_sec = min_sec
    words = count_words(text)
    return round(words / (duration_sec / 60.0), 1)


def wpm_pair(target_text: str, result_text: str, duration_sec: float, quota_sec: float) -> Tuple[float, float]:
    """
    타깃 WPM: target_text를 quota_sec에 읽었다고 가정했을 때의 WPM
    유저 WPM: result_text를 실제 duration_sec로 읽은 WPM
    """
    target_w = count_words(target_text)
    user_w = count_words(result_text)

    target_wpm = round(target_w / (max(quota_sec, 0.3) / 60.0), 1)
    user_wpm = round(user_w / (max(duration_sec, 0.3) / 60.0), 1)
    return target_wpm, user_wpm


def speed_judgment(user_wpm: float, target_wpm: float, *, slow_factor: float = 0.75, fast_factor: float = 1.25) -> str:
    """
    속도 판정:
      - user_wpm < target_wpm * slow_factor  → 'slow'
      - user_wpm > target_wpm * fast_factor  → 'fast'
      - 그 외 → 'ok'
    허용 범위 ±25%
    """
    if target_wpm <= 0:
        return "ok"
    if user_wpm < target_wpm * slow_factor:
        return "slow"
    if user_wpm > target_wpm * fast_factor:
        return "fast"
    return "ok"
