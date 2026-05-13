from agents.state import OSIMASState, ToolName


ALL_TOOLS: list[ToolName] = [
    "tool_market",
    "tool_realestate",
    "tool_industry",
    "tool_valuation",
    "tool_macro",
    "tool_ip",
]

# Phase 1 필수 / Phase 2 선택
PHASE1_TOOLS: list[ToolName] = ["tool_market", "tool_realestate", "tool_industry"]
PHASE2_TOOLS: list[ToolName] = ["tool_valuation", "tool_macro", "tool_ip"]


def plan_tools(state: OSIMASState) -> dict:
    query = state.get("query", "").lower()

    # 쿼리 키워드에 따라 도구 선택
    tools: list[ToolName] = list(PHASE1_TOOLS)

    if any(k in query for k in ["가치", "밸류", "인수", "매각", "투자", "배수"]):
        tools.append("tool_valuation")
    if any(k in query for k in ["원자재", "물류", "공급망", "전력", "비용"]):
        tools.append("tool_macro")
    if any(k in query for k in ["특허", "인증", "기술", "ip", "벤처", "이노비즈"]):
        tools.append("tool_ip")

    # 기본 쿼리면 전체 실행
    if not state.get("requested_tools"):
        tools = ALL_TOOLS

    return {"requested_tools": list(dict.fromkeys(tools))}  # 중복 제거
