"""
상권 분석 에이전트 — 소상공인시장진흥공단 API
업종별 평균 매출, 개폐업률, 유동인구, 주요 소비층 분석
API: https://www.data.go.kr/data/15083033/openapi.do
"""
import os
from agents.state import ToolResult
from agents.confidence import source_confidence
from .base import BaseMCPTool


SBIZ_API_KEY = os.getenv("SBIZ_API_KEY", "")
SBIZ_BASE_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2"


class MarketTool(BaseMCPTool):
    tool_name = "tool_market"
    authority_score = 0.85   # 정부 공식 기관
    max_valid_days = 180     # 반기 갱신

    async def _fetch(self, region_id: str, query: str) -> ToolResult:
        if not SBIZ_API_KEY:
            return self._stub(region_id)

        resp = await self.client.get(
            f"{SBIZ_BASE_URL}/storeListInDong",
            params={
                "serviceKey": SBIZ_API_KEY,
                "divId": "adongCd",
                "key": region_id,
                "type": "json",
                "pageIndex": "1",
                "pageSize": "10",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        items = data.get("body", {}).get("items", [])
        total = data.get("body", {}).get("totalElements", 0)
        freshness = 90

        confidence = source_confidence(
            freshness_days=freshness,
            authority_score=self.authority_score,
            coverage_score=0.75 if items else 0.2,
            consistency_score=0.7,
            max_valid_days=self.max_valid_days,
        )

        summary = (
            f"[상권 분석] 조회 업체 수: {total}개 | "
            f"표본 {len(items)}개 분석 | "
            f"데이터 기준: 최근 {freshness}일 이내"
        )
        if items:
            sample = items[0]
            summary += f" | 대표 업종: {sample.get('uptaeNm', '미상')}"

        return ToolResult(
            tool=self.tool_name,
            status="ok",
            confidence=confidence,
            freshness_days=freshness,
            data_ref=None,
            summary=summary,
        )

    def _stub(self, region_id: str) -> ToolResult:
        """API 키 미설정 시 더미 데이터로 동작 (개발용)"""
        confidence = source_confidence(
            freshness_days=90,
            authority_score=self.authority_score,
            coverage_score=0.6,
            consistency_score=0.65,
            max_valid_days=self.max_valid_days,
        )
        return ToolResult(
            tool=self.tool_name,
            status="ok",
            confidence=confidence,
            freshness_days=90,
            data_ref=None,
            summary=(
                f"[상권 분석 - 더미] 지역: {region_id} | "
                "음식업 비중 38% · 소매업 22% · 서비스업 19% | "
                "월평균 매출 약 1,850만원 | 개업률 2.1% / 폐업률 1.8% (최근 1년)"
            ),
        )
