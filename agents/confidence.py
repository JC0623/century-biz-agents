import math
from .state import ToolResult


def source_confidence(
    freshness_days: int | None,
    authority_score: float,
    coverage_score: float,
    consistency_score: float,
    max_valid_days: int = 365,
) -> float:
    if freshness_days is None:
        freshness = 0.0
    else:
        freshness = max(0.0, 1.0 - freshness_days / max_valid_days)

    score = (
        0.35 * freshness
        + 0.30 * authority_score
        + 0.20 * coverage_score
        + 0.15 * consistency_score
    )
    return round(score, 3)


def should_fallback(tool_results: dict[str, ToolResult]) -> bool:
    if not tool_results:
        return True
    scores = [r["confidence"] for r in tool_results.values() if r["status"] == "ok"]
    if not scores or max(scores) < 0.55:
        return True
    stale = [
        r for r in tool_results.values()
        if r.get("freshness_days") and r["freshness_days"] > 365
    ]
    return len(stale) >= 2


CONFIDENCE_LABELS = {
    (0.75, 1.01): "높음",
    (0.55, 0.75): "보통",
    (0.35, 0.55): "낮음",
    (0.00, 0.35): "매우 낮음",
}


def confidence_label(score: float) -> str:
    for (low, high), label in CONFIDENCE_LABELS.items():
        if low <= score < high:
            return label
    return "알 수 없음"


def confidence_message(score: float) -> str:
    if score >= 0.75:
        return f"분석 신뢰도 {score:.2f}로 높습니다. 데이터가 일관된 방향을 보입니다."
    elif score >= 0.55:
        return f"신뢰도 {score:.2f}. 방향성 판단은 가능하나 일부 데이터 별도 확인을 권장합니다."
    elif score >= 0.35:
        return f"신뢰도 {score:.2f}. 데이터 한계로 방향성만 제시합니다. 투자 전 현장 실사를 권장합니다."
    else:
        return f"신뢰 가능한 공개 데이터가 불충분합니다 (신뢰도 {score:.2f}). 추정 분석은 제공하나 사업 판단 근거로 사용하기엔 제한이 있습니다."
