import os
from agents.state import OSIMASState, ToolResult
from agents.confidence import confidence_message

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


SYSTEM_PROMPT = """당신은 OSI-MAS 공간 비즈니스 분석가입니다.
사실·추정·가정·권고를 반드시 구분하여 제시하십시오.
노후화되거나 희소한 데이터를 확실한 사실처럼 제시하지 마십시오.
한국 비즈니스 커뮤니케이션 스타일: 직접적, 보수적, 의사결정 중심.

출력 구조 (반드시 준수):
1. 결론
2. 신뢰도 (0.00~1.00)
3. 데이터 기준일
4. 근거 (에이전트별 요약)
5. 한계
6. 추가 확인 필요사항

임계값 규칙:
- 신뢰도 < 0.65 → 추가 검증 권고 명시
- 신뢰도 < 0.45 → 확정적 권고 금지"""


def _build_data_block(results: dict[str, ToolResult]) -> str:
    lines = []
    for tool_name, r in results.items():
        status = r["status"]
        if status == "ok":
            lines.append(f"- [{tool_name}] {r['summary']} (신뢰도: {r['confidence']:.2f})")
        else:
            lines.append(f"- [{tool_name}] 상태: {status} / 오류: {r.get('error', '알 수 없음')}")
    return "\n".join(lines)


def _avg_confidence(results: dict[str, ToolResult]) -> float:
    scores = [r["confidence"] for r in results.values() if r["status"] == "ok"]
    return round(sum(scores) / len(scores), 3) if scores else 0.0


async def synthesize(state: OSIMASState) -> dict:
    results = state.get("tool_results", {})
    warnings = state.get("warnings", [])
    avg_conf = _avg_confidence(results)
    data_block = _build_data_block(results)

    if ANTHROPIC_API_KEY:
        report = await _llm_synthesize(state, data_block, avg_conf)
    else:
        report = _rule_based_report(state, data_block, avg_conf, warnings)

    return {"final_report": report}


async def _llm_synthesize(state: OSIMASState, data_block: str, avg_conf: float) -> str:
    try:
        import anthropic
        client = anthropic.AsyncAnthropic()
        user_msg = (
            f"분석 대상 지역: {state['region_id']}\n"
            f"사용자 질문: {state['query']}\n\n"
            f"에이전트 수집 데이터:\n{data_block}\n\n"
            f"종합 신뢰도: {avg_conf:.2f}\n"
            f"위 데이터를 바탕으로 입지 분석 리포트를 작성하세요."
        )
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        return message.content[0].text
    except Exception as e:
        return _rule_based_report(state, data_block, avg_conf, [str(e)])


def _rule_based_report(
    state: OSIMASState,
    data_block: str,
    avg_conf: float,
    warnings: list[str],
) -> str:
    conf_msg = confidence_message(avg_conf)
    warn_block = "\n".join(f"  - {w}" for w in warnings) if warnings else "  없음"

    return f"""
========================================
  OSI-MAS 입지 분석 리포트
========================================
분석 지역 : {state['region_id']}
분석 질문 : {state['query']}

1. 결론
   {conf_msg}

2. 신뢰도
   종합 점수: {avg_conf:.2f} / 1.00

3. 에이전트별 데이터 요약
{data_block}

4. 한계 및 경고
{warn_block}

5. 추가 확인 필요사항
   - API 키 설정 시 실제 공공 데이터 연동 가능
   - 현장 실사 및 최신 카드매출 자료 별도 확인 권장
   - 밸류에이션 수치는 참고용이며 전문가 검토 필요
========================================
"""
