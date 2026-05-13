"""
OSI-MAS CLI 진입점
사용법: python main.py --region "서울특별시 강남구 역삼동" --query "이 지역 식당 인수 적합성 분석"
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _print_banner():
    print("""
================================================
  OSI-MAS  Open Spatial Intelligence
  Multi-Agent System  v0.1.0 (MVP)
================================================
""")


def _print_progress(tool: str, status: str, conf: float | None = None):
    icons = {"ok": "✓", "timeout": "✗", "error": "✗", "running": "…"}
    icon = icons.get(status, "?")
    conf_str = f"  신뢰도: {conf:.2f}" if conf is not None else ""
    print(f"  {icon} {tool:<20} {status}{conf_str}")


async def run(region_id: str, query: str, verbose: bool = False):
    from agents.graph import graph

    _print_banner()
    print(f"분석 지역 : {region_id}")
    print(f"분석 질문 : {query}")
    print("\n에이전트 실행 중...\n")

    initial_state = {
        "query": query,
        "region_id": region_id,
        "requested_tools": [],
        "tool_results": {},
        "warnings": [],
    }

    final_state = await graph.ainvoke(initial_state)

    if verbose:
        print("\n[에이전트별 결과]")
        for tool_name, result in final_state.get("tool_results", {}).items():
            _print_progress(tool_name, result["status"], result.get("confidence"))

    print(final_state.get("final_report", "리포트 생성 실패"))

    warnings = final_state.get("warnings", [])
    if warnings:
        print("\n[경고]")
        for w in warnings:
            print(f"  ! {w}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="OSI-MAS: 공공 데이터 기반 입지 분석 멀티 에이전트"
    )
    parser.add_argument(
        "--region", "-r",
        default="서울특별시 강남구 역삼동",
        help="분석 대상 지역 (행정동명 또는 주소)",
    )
    parser.add_argument(
        "--query", "-q",
        default="이 지역의 소규모 식당 인수 적합성을 분석해줘",
        help="분석 질문",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="에이전트별 상세 결과 출력",
    )

    args = parser.parse_args()
    asyncio.run(run(args.region, args.query, args.verbose))


if __name__ == "__main__":
    main()
