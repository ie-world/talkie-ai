from __future__ import annotations
from typing import Dict, List, Literal, Tuple

from app.utils.wpm import normalize, speed_judgment, count_words

Issue = Literal["accuracy", "speed_fast", "speed_slow", "gaps", "good"]


# ===== 텍스트 정확성 =====
def is_text_accurate(target_text: str, result_text: str) -> bool:
    """
    normalize 후 완전 동일해야 '정확'으로 간주
    """
    return normalize(target_text) == normalize(result_text)


# ===== 속도(WPM) 계산 유틸 =====
def _wpm_pair_by_durations(
    target_text: str,
    result_text: str,
    target_duration_sec: float,
    user_duration_sec: float,
) -> Tuple[float, float]:
    """
    타깃/사용자 발화 시간을 '초'로 받아 WPM을 계산
    - target_duration_sec: ref_graph 길이 기반(샘플레이트 50Hz)
    - user_duration_sec: usr_graph 길이 기반(샘플레이트 50Hz) 또는 실제 녹음 길이
    """
    
    td = max(float(target_duration_sec or 0), 0.3) # 최소 분모 보호(0.3초)
    ud = max(float(user_duration_sec or 0), 0.3)

    tw = count_words(target_text)
    uw = count_words(result_text)

    wpm_target = round(tw / (td / 60.0), 1)
    wpm_user = round(uw / (ud / 60.0), 1)
    return wpm_target, wpm_user


# ===== 속도(WPM) 판정 =====
def judge_speed(
    target_text: str,
    result_text: str,
    *,
    user_duration_sec: float,
    target_duration_sec: float,
    slow_factor: float = 0.75,
    fast_factor: float = 1.25,
) -> Tuple[str, float, float]:
    """
    - target WPM: target_duration_sec 안에 target_text를 읽는다고 가정한 속도
    - user WPM: user_duration_sec 동안 result_text를 읽은 실제 속도
    - 판정: 기본 허용 범위 ±25%
    """
    wpm_target, wpm_user = _wpm_pair_by_durations(
        target_text, result_text, target_duration_sec, user_duration_sec
    )
    spd = speed_judgment(wpm_user, wpm_target, slow_factor=slow_factor, fast_factor=fast_factor)
    return spd, wpm_target, wpm_user


# ===== 파형 공백(gaps) 판정 =====
def _total_silence_seconds(
    series: List[int],
    sample_rate_hz: int = 50,
    threshold_mode: Literal["percentile", "rel"] = "percentile",
    perc: float = 0.15,
    rel_ratio: float = 0.25,
    min_run_samples: int = 4,
) -> float:
    """
    시퀀스에서 공백 구간 총 길이(초)를 추정
    - percentile 모드: 시퀀스의 p-백분위수(디폴트 15%) 이하를 침묵으로 간주
    - rel 모드: max 값의 rel_ratio(디폴트 25%) 이하를 침묵으로 간주
    - 최소 연속 길이: min_run_samples 샘플 이상일 때만 공백으로 합산 (50Hz 기준 4샘플=0.08s)
    """
    if not series:
        return 0.0

    if threshold_mode == "percentile":
        arr = sorted(series)
        idx = max(0, min(len(arr) - 1, int(len(arr) * perc)))
        thr = arr[idx]
    else:  # rel모드
        thr = max(series) * rel_ratio

    # 연속 below-threshold 구간 길이 합산
    run = 0
    total_samples = 0
    for v in series:
        if v <= thr:
            run += 1
        else:
            if run >= min_run_samples:
                total_samples += run
            run = 0
    if run >= min_run_samples:
        total_samples += run

    return total_samples / float(sample_rate_hz)


def detect_gaps(
    ref_graph: List[int],
    usr_graph: List[int],
    *,
    sample_rate_hz: int = 50,
    mode: Literal["percentile", "rel"] = "percentile",
    perc: float = 0.15,
    rel_ratio: float = 0.25,
    min_run_samples: int = 4,
    tolerance_ratio: float = 1.3,
    min_gap_seconds: float = 0.20,
) -> bool:
    """
    사용자의 '침묵 총 길이'가 기준보다 현저히 크면 공백 이슈로 간주
    - tolerance_ratio: 사용자 침묵이 기준의 1.3배 이상이면 공백 이슈
    - min_gap_seconds: 기준이 0에 매우 가깝더라도, 사용자의 총 침묵이 이 값 이상이면 이슈로 간주
    """
    ref_sil = _total_silence_seconds(
        ref_graph, sample_rate_hz=sample_rate_hz, threshold_mode=mode,
        perc=perc, rel_ratio=rel_ratio, min_run_samples=min_run_samples
    )
    usr_sil = _total_silence_seconds(
        usr_graph, sample_rate_hz=sample_rate_hz, threshold_mode=mode,
        perc=perc, rel_ratio=rel_ratio, min_run_samples=min_run_samples
    )

    gaps_flag = False
    if usr_sil >= min_gap_seconds:
        # 기준 대비 현저히 큰지
        if ref_sil == 0:
            gaps_flag = True
        else:
            gaps_flag = (usr_sil >= ref_sil * tolerance_ratio)

    return gaps_flag


# ===== 최종 이슈 결정 =====
def decide_issue(accuracy_ok: bool, speed: str, gaps: bool) -> Issue:
    """
    우선순위:
      1) 정확성 문제 (accuracy=false)
      2) 속도 문제 ('fast'/'slow')
      3) 공백 문제 (gaps=true)
      4) 그 외 'good'
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


# ===== 최종 분석 =====
def analyze_feedback(
    *,
    target_text: str,
    result_text: str,
    target_duration_sec: float,
    user_duration_sec: float,
    ref_graph: List[int],
    usr_graph: List[int],
) -> Dict:

    # 1) 정확성
    acc_ok = is_text_accurate(target_text, result_text)

    # 2) 속도
    spd, wpm_target, wpm_user = judge_speed(
        target_text=target_text,
        result_text=result_text,
        user_duration_sec=float(user_duration_sec),
        target_duration_sec=float(target_duration_sec),
    )

    # 3) 공백
    gaps_flag = detect_gaps(
        ref_graph=ref_graph,
        usr_graph=usr_graph,
        sample_rate_hz=50,
        mode="percentile",
        perc=0.15,
        rel_ratio=0.25,
        min_run_samples=4,
        tolerance_ratio=1.3,
        min_gap_seconds=0.10,
    )

    # 4) 최종 이슈
    issue = decide_issue(acc_ok, spd, gaps_flag)

    return {
        "issue": issue,
        "accuracy_ok": acc_ok,
        "speed": "ok" if spd not in ("fast", "slow") else spd,
        "gaps": gaps_flag,
        "wpm_target": wpm_target,
        "wpm_user": wpm_user,
    }
