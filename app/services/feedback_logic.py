# ------------------------------------------------------------
# SEGMENTS(단어별 타임스탬프)를 이용해 정확도/속도/공백을 판정하는 로직
# - 입력:
#     - target_text: 기준 문장
#     - result_text: STT 결과 문장
#     - user_segments: 사용자 발화의 세그먼트 목록
# - 출력:
#     issue, accuracy_ok, speed, gaps, wpm_user
#     + 참고지표(wps_total, wps_art, pause_ms, longest_pause_ms, total_ms, speech_ms, n_words)
# ------------------------------------------------------------

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Literal
import re

Issue = Literal["accuracy", "speed_fast", "speed_slow", "gaps", "good"]

# ===================== 튜닝 가능한 임계치 =====================

# --- 정확도(WER) ---
WER_THRESHOLD = 0.20  # 20% 초과면 정확도 이슈

# --- 속도 ---
ABS_FAST_WPS = 1.90          # 초당 단어수(총시간 기준) ≥ 1.90 → fast
ABS_FAST_WPS_ART = 2.60      # 초당 단어수(발화시간 기준) ≥ 2.60 → fast
ABS_SLOW_WPS = 1.00          # 초당 단어수 ≤ 1.00 + 아래 조건 → slow
ABS_SLOW_MIN_SPEECH_MS = 2000  # 느림 판정은 실제 말한 시간이 2.0s 이상일 때만

# 극단적 빠름 보호장치
EXTREME_FAST_MAX_TOTAL_MS = 1000  # 총 길이 < 1.0s 이면서
EXTREME_FAST_MIN_WORDS = 5        # 단어수 ≥ 5 → fast

# --- 공백 ---
PAUSE_RATIO_THRESHOLD = 0.35      # 전체의 35% 이상이 침묵이면 gaps
LONGEST_PAUSE_MS_THRESHOLD = 500  # 최장 침묵 ≥ 0.5s 이면 gaps

# =============================================================

# -------------------- 텍스트 정규화 & WER --------------------

_SPACES = re.compile(r"\s+")
_PUNCTS = re.compile(r"[^\w\s]")  # 구두점 제거(한글/영문/숫자/밑줄 제외)

def _normalize(text: str) -> str:
    """
    한국어용 간단 정규화
    - 소문자
    - 구두점 제거
    - 다중 공백 정리
    """
    t = text.strip().lower()
    t = _PUNCTS.sub(" ", t)
    t = _SPACES.sub(" ", t)
    return t.strip()

def _wer(ref: str, hyp: str) -> float:
    """
    WER(Word Error Rate) 계산
    - 공백 기준 토큰화
    - 편집거리(삽입/삭제/치환)
    """
    r = _normalize(ref).split()
    h = _normalize(hyp).split()
    if not r and not h:
        return 0.0
    # DP 테이블
    R, H = len(r), len(h)
    d = [[0]*(H+1) for _ in range(R+1)]
    for i in range(R+1): d[i][0] = i
    for j in range(H+1): d[0][j] = j
    for i in range(1, R+1):
        for j in range(1, H+1):
            cost = 0 if r[i-1] == h[j-1] else 1
            d[i][j] = min(
                d[i-1][j] + 1,      # 삭제
                d[i][j-1] + 1,      # 삽입
                d[i-1][j-1] + cost  # 치환
            )
    return d[R][H] / max(1, R)

# -------------------- 세그먼트 메트릭 --------------------

@dataclass
class SegMetrics:
    total_ms: int          # 전체 구간 길이
    speech_ms: int         # 실제 말한 시간(단어 duration 합)
    pause_ms: int          # 전체 침묵 시간
    longest_pause_ms: int  # 최장 침묵 길이
    n_words: int           # 단어 수
    wps_total: float       # 초당 단어수 (총시간 기준)
    wps_art: float         # 초당 단어수 (순수 발화시간 기준: 아티큘레이션 속도)

def _merge_segments(segments: List[dict]) -> dict:
    """
    여러 세그먼트가 오면 하나로 병합.
    - start: 최소, end: 최대
    - words: 전부 모아 시작시간 기준 정렬
    words 포맷: [start_ms, end_ms, "token"]
    """
    if not segments:
        return {"start": 0, "end": 0, "words": []}
    s_min = min(int(s.get("start", 0)) for s in segments)
    e_max = max(int(s.get("end", s_min)) for s in segments)
    words = []
    for s in segments:
        for w in s.get("words", []):
            if isinstance(w, dict):
                ws = int(w.get("start", 0))
                we = int(w.get("end", ws))
                tok = str(w.get("token", ""))
                words.append((ws, we, tok))
            elif isinstance(w, (list, tuple)) and len(w) >= 2:
                ws, we = int(w[0]), int(w[1])
                tok = str(w[2]) if len(w) >= 3 else ""
                words.append((ws, we, tok))
    words.sort(key=lambda x: x[0])
    return {"start": s_min, "end": e_max, "words": words}

def _metrics_from_segments(segments: List[dict]) -> SegMetrics:
    """
    segments → 메트릭 추출 (ms 단위)
    """
    merged = _merge_segments(segments)
    start = int(merged.get("start", 0))
    end = int(merged.get("end", start))
    total_ms = max(0, end - start)

    words = merged.get("words", [])
    durations = [max(0, we - ws) for (ws, we, _tok) in words]
    n_words = len(durations)
    speech_ms = sum(durations)

    gaps = []
    for i in range(len(words) - 1):
        prev_end = words[i][1]
        next_start = words[i+1][0]
        gaps.append(max(0, next_start - prev_end))
    pause_ms = sum(gaps)
    longest_pause_ms = max(gaps) if gaps else 0

    total_sec = max(total_ms / 1000.0, 1e-3)
    speech_sec = max(speech_ms / 1000.0, 1e-3)

    wps_total = round(n_words / total_sec, 2)
    wps_art   = round(n_words / speech_sec, 2)

    return SegMetrics(
        total_ms=total_ms,
        speech_ms=speech_ms,
        pause_ms=pause_ms,
        longest_pause_ms=longest_pause_ms,
        n_words=n_words,
        wps_total=wps_total,
        wps_art=wps_art,
    )

# -------------------- 판정 로직 --------------------

def _speed_from_metrics(user: SegMetrics) -> str:
    """
    절대 임계치 기반 속도 판정 + 극단적 빠름 보호장치
    """
    # 아주 짧은 시간에 단어가 많은 경우: fast
    if user.total_ms < EXTREME_FAST_MAX_TOTAL_MS and user.n_words >= EXTREME_FAST_MIN_WORDS:
        return "fast"

    if user.wps_total >= ABS_FAST_WPS or user.wps_art >= ABS_FAST_WPS_ART:
        return "fast"

    if user.wps_total <= ABS_SLOW_WPS and user.speech_ms >= ABS_SLOW_MIN_SPEECH_MS:
        return "slow"

    return "ok"

def _gaps_from_metrics(user: SegMetrics) -> bool:
    """
    공백 판정:
      - 전체 중 침묵 비율이 높거나
      - 최장 침묵이 길면 gaps=True
    """
    if user.total_ms <= 0:
        return False
    pause_ratio = user.pause_ms / user.total_ms
    if pause_ratio >= PAUSE_RATIO_THRESHOLD:
        return True
    if user.longest_pause_ms >= LONGEST_PAUSE_MS_THRESHOLD:
        return True
    return False

def decide_issue(accuracy_ok: bool, speed: str, gaps: bool) -> Issue:
    """
    우선순위:
      1) 정확성
      2) 속도
      3) 공백
      4) 양호
    """
    if not accuracy_ok:
        return "accuracy"
    if speed == "fast":
        return "speed_fast"
    if speed == "slow":
        return "speed_slow"
    if gaps:
        return "gaps"
    return "good"

# -------------------- 메인: 세그먼트 기반 분석 --------------------

def analyze_feedback_with_segments(
    *,
    target_text: str,
    result_text: str,
    user_segments: List[dict],
) -> Dict:
    """
    segments만으로 정확도/속도/공백을 분석한다.
    """
    # 1) 정확도(WER)
    wer_val = _wer(target_text, result_text)
    accuracy_ok = (wer_val <= WER_THRESHOLD)

    # 2) 메트릭 추출
    m = _metrics_from_segments(user_segments)

    # 3) 속도/공백 판정
    speed = _speed_from_metrics(m)
    gaps = _gaps_from_metrics(m)

    # 4) 최종 이슈
    issue = decide_issue(accuracy_ok, speed, gaps)

    # 5) 반환 (WPM: 분당 단어수)
    return {
        "issue": issue,
        "accuracy_ok": accuracy_ok,
        "speed": speed,                # "fast" | "slow" | "ok"
        "gaps": gaps,
        "wpm_user": round(m.wps_total * 60.0, 1),

        # 튜닝용 참고 지표
        "wer": round(wer_val, 3),
        "wps_total": m.wps_total,
        "wps_art": m.wps_art,
        "pause_ms": m.pause_ms,
        "longest_pause_ms": m.longest_pause_ms,
        "total_ms": m.total_ms,
        "speech_ms": m.speech_ms,
        "n_words": m.n_words,
    }
