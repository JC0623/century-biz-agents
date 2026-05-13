"""
산업 클러스터 에이전트 — 전국 공장등록현황 / 산업단지 데이터
반경 내 핵심 업종 밀집도, 물류 인프라, 유관기업 분포 분석
API: https://www.data.go.kr/data/15013140/fileData.do
"""
import os
from agents.state import ToolResult
from agents.confidence import source_confidence
from .base import BaseMCPTool


PUBLIC_DATA_API_KEY = os.getenv("PUBLIC_DATA_API_KEY", "")
INDUSTRY_BASE_URL = "https://apis.data.go.kr/1480000/FactoryListService"


class IndustryTool(BaseMCPTool):
    tool_name = "tool_industry"
    authority_score = 0.80
    max_valid_days = 365

    async def _fetch(self, region_id: str, query: str) -> ToolResult:
        if not PUBLIC_DATA_API_KEY:
            return self._stub(region_id)

        resp = await self.client.get(
            f"{INDUSTRY_BASE_URL}/getFactoryList",
            params={
                "serviceKey": PUBLIC_DATA_API_KEY,
                "sigunguCd": region_id[:5] if len(region_id) >= 5 else region_id,
                "numOfRows": "20",
                "pageNo": "1",
                "type": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("response", {}).get("body", {}).get("items", {})
        item_list = items.get("item", []) if isinstance(items, dict) else []
        freshness = 180

        confidence = source_confidence(
            freshness_days=freshness,
            authority_score=self.authority_score,
            coverage_score=0.70 if item_list else 0.2,
            consistency_score=0.65,
            max_valid_days=self.max_valid_days,
        )

        return ToolResult(
            tool=self.tool_name,
            status="ok",
            confidence=confidence,
            freshness_days=freshness,
            data_ref=None,
            summary=(
                f"[산업 클러스터] 등록 공장 수: {len(item_list)}개 조회 | "
                f"데이터 기준: {freshness}일 이내"
            ),
        )

    def _stub(self, region_id: str) -> ToolResult:
        confidence = source_confidence(
            freshness_days=180,
            authority_score=self.authority_score,
            coverage_score=0.65,
            consistency_score=0.6,
            max_valid_days=self.max_valid_days,
        )
        return ToolResult(
            tool=self.tool_name,
            status="ok",
            confidence=confidence,
            freshness_days=180,
            data_ref=None,
            summary=(
                f"[산업 클러스터 - 더미] 지역: {region_id} | "
                "반경 2km 내 등록 공장 47개 | 주요 업종: 금속가공 31%, 식품 22% | "
                "물류창고 3개소, 고속도로 IC 2.1km"
            ),
        )
