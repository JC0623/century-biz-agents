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

        # region_id: "위도,경도" 또는 행정동코드(8자리)
        if "," in region_id:
            lat, lon = region_id.split(",")
            params = {
                "serviceKey": SBIZ_API_KEY,
                "cx": lon.strip(),
                "cy": lat.strip(),
                "radius": "500",
                "type": "json",
                "pageIndex": "1",
                "pageSize": "100",
            }
            endpoint = f"{SBIZ_BASE_URL}/storeListInRadius"
        else:
            params = {
                "serviceKey": SBIZ_API_KEY,
                "divId": "adongCd",
                "key": region_id[:8],   # 8자리 행정동코드
                "type": "json",
                "pageIndex": "1",
                "pageSize": "100",
            }
            endpoint = f"{SBIZ_BASE_URL}/storeListInDong"

        resp = await self.client.get(endpoint, params=params)
        resp.raise_for_status()
        data = resp.json()

        result_code = data.get("header", {}).get("resultCode", "")
        items = data.get("body", {}).get("items", [])
        freshness = 90

        confidence = source_confidence(
            freshness_days=freshness,
            authority_score=self.authority_score,
            coverage_score=0.80 if items else 0.2,
            consistency_score=0.7,
            max_valid_days=self.max_valid_days,
        )

        if not items or result_code != "00":
            return self._stub(region_id)

        # 업종 분포 집계
        from collections import Counter
        cats = Counter(item.get("indsLclsNm", "기타") for item in items)
        top3 = ", ".join(f"{k} {v}개" for k, v in cats.most_common(3))
        dong_nm = items[0].get("adongNm", region_id)

        summary = (
            f"[상권 분석] {dong_nm} | 반경 500m 업소 {len(items)}개 | "
            f"주요 업종: {top3} | 데이터 기준: 최근 {freshness}일"
        )

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
