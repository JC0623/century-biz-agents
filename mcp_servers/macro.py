"""
거시 원가·공급망 에이전트 — 한국은행 ECOS API
핵심 원자재 가격, 물류비 지수, 산업용 전력비, 금리 추이 분석
ECOS API: https://ecos.bok.or.kr/api/
"""
import os
from datetime import datetime
from agents.state import ToolResult
from agents.confidence import source_confidence
from .base import BaseMCPTool


ECOS_API_KEY = os.getenv("ECOS_API_KEY", "")
ECOS_BASE_URL = "https://ecos.bok.or.kr/api"


class MacroTool(BaseMCPTool):
    tool_name = "tool_macro"
    authority_score = 0.90   # 한국은행 공식
    max_valid_days = 60

    async def _fetch(self, region_id: str, query: str) -> ToolResult:
        if not ECOS_API_KEY:
            return self._stub(region_id)

        # 생산자물가지수 (PPI) 조회 — 전월 기준 (1월이면 전년 12월)
        now = datetime.now()
        if now.month == 1:
            year, month = now.year - 1, 12
        else:
            year, month = now.year, now.month - 1
        period = f"{year}{month:02d}"

        resp = await self.client.get(
            f"{ECOS_BASE_URL}/StatisticSearch/{ECOS_API_KEY}/json/kr/1/5/404Y014/MM/{period}/{period}",
        )
        resp.raise_for_status()
        data = resp.json()
        freshness = 30

        confidence = source_confidence(
            freshness_days=freshness,
            authority_score=self.authority_score,
            coverage_score=0.70,
            consistency_score=0.75,
            max_valid_days=self.max_valid_days,
        )

        return ToolResult(
            tool=self.tool_name,
            status="ok",
            confidence=confidence,
            freshness_days=freshness,
            data_ref=None,
            summary=(
                f"[거시 원가] 한국은행 ECOS 생산자물가지수 조회 완료 | "
                f"기준: {period}"
            ),
        )

    def _stub(self, region_id: str) -> ToolResult:
        confidence = source_confidence(
            freshness_days=30,
            authority_score=self.authority_score,
            coverage_score=0.7,
            consistency_score=0.75,
            max_valid_days=self.max_valid_days,
        )
        return ToolResult(
            tool=self.tool_name,
            status="ok",
            confidence=confidence,
            freshness_days=30,
            data_ref=None,
            summary=(
                "[거시 원가 - 더미] 생산자물가지수 YoY +2.3% | "
                "산업용 전력단가 kWh당 119.4원 (+8.1% YoY) | "
                "물류비 지수 108.2 (전년 동기 대비 +3.7%) | "
                "기준금리 3.50% (동결)"
            ),
        )
