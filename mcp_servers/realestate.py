"""
공간 가치 에이전트
- 국토교통부 상업업무용 부동산 매매 실거래가 (RTMSDataSvcNrgTrade)
- 국토교통부 건축물대장 총괄표제부 (BldRgstHubService)
"""
import os
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta
from agents.state import ToolResult
from agents.confidence import source_confidence
from .base import BaseMCPTool


MOLIT_API_KEY = os.getenv("MOLIT_API_KEY", "")
BUILDING_API_KEY = os.getenv("BUILDING_API_KEY", "")
MOLIT_BASE_URL = "https://apis.data.go.kr/1613000"

DEFAULT_SGG_CD = "11680"   # 강남구
DEFAULT_DONG_CD = "10100"  # 역삼동


def _region_to_sgg(region_id: str) -> str:
    """region_id에서 시군구 코드 5자리 추출. 좌표 형식이면 기본값 사용."""
    # "위도,경도" 형식이면 기본 SGG 코드 반환
    if "." in region_id and "," in region_id:
        return DEFAULT_SGG_CD
    digits = "".join(filter(str.isdigit, region_id))
    return digits[:5] if len(digits) >= 5 else DEFAULT_SGG_CD


class RealEstateTool(BaseMCPTool):
    tool_name = "tool_realestate"
    authority_score = 0.90
    max_valid_days = 90

    async def _fetch(self, region_id: str, query: str) -> ToolResult:
        if not MOLIT_API_KEY:
            return self._stub(region_id)

        # 최근 3개월치 조회 (데이터 공백 방지)
        results = []
        for months_ago in range(0, 3):
            dt = datetime.now() - timedelta(days=30 * months_ago)
            ym = dt.strftime("%Y%m")
            sgg_cd = _region_to_sgg(region_id)

            resp = await self.client.get(
                f"{MOLIT_BASE_URL}/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade",
                params={
                    "serviceKey": MOLIT_API_KEY,
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
                break  # 데이터 있으면 중단

        freshness = 60
        if not results:
            return self._stub(region_id)

        # 거래금액(만원) 파싱 및 평당가 계산
        deals = []
        for item in results:
            try:
                amount = int(item.findtext("dealAmount", "0").replace(",", ""))
                area = float(item.findtext("buildingAr", "0") or "0")
                land_use = item.findtext("landUse", "").strip()
                building_use = item.findtext("buildingUse", "").strip()
                umd = item.findtext("umdNm", "").strip()
                if amount > 0 and area > 0:
                    pyeong = area / 3.3058
                    per_pyeong = amount / pyeong
                    deals.append({
                        "amount": amount,
                        "area_m2": area,
                        "per_pyeong": per_pyeong,
                        "land_use": land_use,
                        "building_use": building_use,
                        "umd": umd,
                    })
            except (ValueError, TypeError):
                continue

        if not deals:
            return self._stub(region_id)

        avg_per_pyeong = sum(d["per_pyeong"] for d in deals) / len(deals)
        avg_amount = sum(d["amount"] for d in deals) / len(deals)
        land_uses = list({d["land_use"] for d in deals if d["land_use"]})[:3]
        bldg_uses = list({d["building_use"] for d in deals if d["building_use"]})[:3]

        # 건축물대장 조회 (용적률·건폐율·주용도)
        bldg_info = await self._fetch_building_registry(sgg_cd)

        confidence = source_confidence(
            freshness_days=freshness,
            authority_score=self.authority_score,
            coverage_score=min(0.95, 0.5 + len(deals) * 0.01),
            consistency_score=0.85,
            max_valid_days=self.max_valid_days,
        )

        summary = (
            f"[공간 가치] {sgg_cd} 기준 실거래 {len(deals)}건 | "
            f"평균 거래가 {avg_amount/10000:.1f}억원 | "
            f"평당 평균 {avg_per_pyeong:,.0f}만원 | "
            f"용도지역: {', '.join(land_uses) or '미상'} | "
            f"건물용도: {', '.join(bldg_uses) or '미상'}"
        )
        if bldg_info:
            summary += f" | {bldg_info}"

        return ToolResult(
            tool=self.tool_name,
            status="ok",
            confidence=confidence,
            freshness_days=freshness,
            data_ref=None,
            summary=summary,
        )

    async def _fetch_building_registry(self, sgg_cd: str) -> str:
        """건축물대장 총괄표제부 — 용적률·건폐율·주용도 집계."""
        if not BUILDING_API_KEY:
            return ""
        try:
            resp = await self.client.get(
                f"{MOLIT_BASE_URL}/BldRgstHubService/getBrRecapTitleInfo",
                params={
                    "serviceKey": BUILDING_API_KEY,
                    "sigunguCd": sgg_cd,
                    "bjdongCd": DEFAULT_DONG_CD,
                    "numOfRows": "50",
                    "pageNo": "1",
                    "type": "json",
                },
            )
            root = ET.fromstring(resp.text)
            items = root.findall(".//item")
            if not items:
                return ""

            vl_rats, bc_rats, purposes = [], [], []
            for item in items:
                try:
                    vl = float(item.findtext("vlRat", "0") or "0")
                    bc = float(item.findtext("bcRat", "0") or "0")
                    purp = item.findtext("mainPurpsCdNm", "").strip()
                    if vl > 0:
                        vl_rats.append(vl)
                    if bc > 0:
                        bc_rats.append(bc)
                    if purp:
                        purposes.append(purp)
                except (ValueError, TypeError):
                    continue

            avg_vl = sum(vl_rats) / len(vl_rats) if vl_rats else 0
            avg_bc = sum(bc_rats) / len(bc_rats) if bc_rats else 0
            top_purp = ", ".join(k for k, _ in Counter(purposes).most_common(3))

            return (
                f"건축물대장 {len(items)}동 | "
                f"평균 용적률 {avg_vl:.0f}% | 평균 건폐율 {avg_bc:.0f}% | "
                f"주용도: {top_purp or '미상'}"
            )
        except Exception:
            return ""

    def _stub(self, region_id: str) -> ToolResult:
        confidence = source_confidence(
            freshness_days=60,
            authority_score=self.authority_score,
            coverage_score=0.6,
            consistency_score=0.75,
            max_valid_days=self.max_valid_days,
        )
        return ToolResult(
            tool=self.tool_name,
            status="ok",
            confidence=confidence,
            freshness_days=60,
            data_ref=None,
            summary=(
                f"[공간 가치 - 더미] 지역: {region_id} | "
                "용도지역: 일반상업지역 | 평균 평당 실거래가 약 3,200만원 | "
                "인근 유사 건물 대비 ±15% 범위 내"
            ),
        )
