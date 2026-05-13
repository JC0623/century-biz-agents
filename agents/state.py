from typing import Annotated, Literal, TypedDict, NotRequired
from operator import add


ToolName = Literal[
    "tool_market",
    "tool_realestate",
    "tool_industry",
    "tool_valuation",
    "tool_macro",
    "tool_ip",
]


class ToolResult(TypedDict):
    tool: ToolName
    status: Literal["ok", "timeout", "error", "skipped"]
    confidence: float        # 0.0 ~ 1.0
    freshness_days: int | None
    data_ref: str | None     # 외부 저장소 포인터 (MVP에서는 미사용)
    summary: str             # 2KB 상한 요약
    error: NotRequired[str]


def merge_results(
    left: dict[str, ToolResult],
    right: dict[str, ToolResult],
) -> dict[str, ToolResult]:
    return {**left, **right}


class OSIMASState(TypedDict):
    query: str
    region_id: str           # 행정동 코드 또는 주소 문자열
    requested_tools: list[ToolName]
    tool_results: Annotated[dict[str, ToolResult], merge_results]
    warnings: Annotated[list[str], add]
    final_report: NotRequired[str]
