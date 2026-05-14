"""
산업 클러스터 에이전트
- 국토교통부 공장·창고 실거래가 (RTMSDataSvcInduTrade)
- 국토교통부 건축물대장 (BldRgstHubService)
"""
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from agents.state import ToolResult
from agents.confidence import source_confidence
from .base import BaseMCPTool


FACTORY_TRADE_API_KEY = os.getenv("FACTORY_TRADE_API_KEY", "")
BUILDING_API_KEY = os.getenv("BUILDING_API_KEY", "")
MOLIT_BASE_URL = "https://apis.data.go.kr/1613000"
DEFAULT_SGG_CD = "11680"


def _to_sgg(region_id: str) -> str:
    if "." in region_id and "," in region_id:
        return DEFAULT_SGG_CD
    digits = "".join(filter(str.isdigit, region_id))
    return digits[:5] if len(digits) >= 5 else DEFAULT_SGG_CD


class IndustryTool(BaseMCPTool):
    tool_name = "tool_industry"
    authority_score = 0.88
    max_valid_days = 180

    async def _fetch(self, region_id: str, query: str) -> ToolResult:
        if not FACTORY_TRADE_API_KEY:
            return self._stub(region_id)

        sgg_cd = _to_sgg(region_id)
        results = []

        for months_ago in range(0, 6):
            dt = datetime.now() - timedelta(days=30 * months_ago)
            ym = dt.strftime("%Y%m")
            resp = await self.client.get(
                f"{MOLIT_BASE_URL}/RTMSDataSvcInduTrade/getRTMSDataSvcInduTrade",
                params={
                    "serviceKey": FACTORY_TRADE_API_KEY,
                    "LAWD_CD": sgg_cd,
                    "DEAL_YMD": ym,
                    "numOfRows": "50",
                    "pageNo": "1",
                },
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            items = root.findall(".//item")
            if items:
                results.extend(items)
                break

        freshness = 90
        if not results:
            return self._stub(region_id)

        deals = []
        bldg_uses = []
        for item in results:
            try:
                amount = int(item.findtext("dealAmount", "0").replace(",", ""))
                area = float(item.findtext("buildingAr", "0") or "0")
                use = item.findtext("buildingUse", "").strip()
                if use:
                    bldg_uses.append(use)
                if amount > 0 and area > 0:
                    deals.append({"amount": amount, "area": area,
                                  "per_pyeong": amount / (area / 3.3058)})
            except (ValueError, TypeError):
                continue

        from collections import Counter
        top_uses = ", ".join(f"{k}({v}건)" for k, v in Counter(bldg_uses).most_common(3))
        avg_price = sum(d["per_pyeong"] for d in deals) / len(deals) if deals else 0

        confidence = source_confidence(
            freshness_days=freshness,
            authority_score=self.authority_score,
            coverage_score=min(0.90, 0.4 + len(results) * 0.01),
            consistency_score=0.80,
            max_valid_days=self.max_valid_days,
        )

        return ToolResult(
            tool=self.tool_name,
            status="ok",
            confidence=confidence,
            freshness_days=freshness,
            data_ref=None,
            summary=(
                f"[산업 클러스터] {sgg_cd} 공장·창고 거래 {len(results)}건 | "
                f"주요 건물용도: {top_uses or '미상'} | "
                f"평균 평당가: {avg_price/10000:.0f}만원"
            ),
        )

    def _stub(self, region_id: str) -> ToolResult:
        confidence = source_confidence(
            freshness_days=180,
            authority_score=self.authority_score,
            coverage_score=0.55,
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
                "반경 2km 내 공장·창고 거래 12건 | 주요 용도: 공장(7건), 창고(5건) | "
                "평균 평당가 약 450만원"
            ),
        )
