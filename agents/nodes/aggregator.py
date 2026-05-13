from agents.state import OSIMASState, ToolResult
from agents.confidence import should_fallback, confidence_message


def aggregate_results(state: OSIMASState) -> dict:
    results = state.get("tool_results", {})
    ok = [r for r in results.values() if r["status"] == "ok"]
    failed = [r for r in results.values() if r["status"] in ("timeout", "error")]

    warnings = []

    if failed:
        failed_names = ", ".join(r["tool"] for r in failed)
        warnings.append(f"다음 도구 응답 실패: {failed_names}")

    if len(ok) < 2:
        warnings.append("사용 가능한 공공데이터가 부족하여 분석 신뢰도가 낮습니다.")

    return {"warnings": warnings}


def quality_gate(state: OSIMASState) -> str:
    results = state.get("tool_results", {})
    if should_fallback(results):
        return "fallback"
    return "synthesize"
