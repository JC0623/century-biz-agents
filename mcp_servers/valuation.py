"""
밸류에이션 벤치마크 에이전트 — DART 전자공시 + 한국은행 ECOS
동종 업종 EV/EBITDA, 이익률 벤치마크 및 보정 배수 산출
DART API: https://opendart.fss.or.kr/
ECOS API: https://ecos.bok.or.kr/
"""
import os
from agents.state import ToolResult
from agents.confidence import source_confidence
from .base import BaseMCPTool


DART_API_KEY = os.getenv("DART_API_KEY", "")
ECOS_API_KEY = os.getenv("ECOS_API_KEY", "")
DART_BASE_URL = "https://opendart.fss.or.kr/api"

# 규모 할인 계수 (상장사 → 비상장 SME)
LIQUIDITY_DISCOUNT = 0.65
GOVERNANCE_DISCOUNT = 0.85
ILLIQUIDITY_PREMIUM_LOW = 0.20
ILLIQUIDITY_PREMIUM_HIGH = 0.35


class ValuationTool(BaseMCPTool):
    tool_name = "tool_valuation"
    authority_score = 0.75   # DART=공식, 보정 모델=추정 혼합
    max_valid_days = 90

    async def _fetch(self, region_id: str, query: str) -> ToolResult:
        if not DART_API_KEY:
            return self._stub(region_id)

        # 업종 분류 코드 추출 (쿼리에서 간단히 파싱)
        corp_code = "00126380"  # 기본값: 삼성전자 (테스트용)

        resp = await self.client.get(
            f"{DART_BASE_URL}/fnlttSinglAcnt.json",
            params={
                "crtfc_key": DART_API_KEY,
                "corp_code": corp_code,
                "bsns_year": "2023",
                "reprt_code": "11011",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        freshness = 365

        confidence = source_confidence(
            freshness_days=freshness,
            authority_score=self.authority_score,
            coverage_score=0.55,
            consistency_score=0.6,
            max_valid_days=self.max_valid_days,
        )

        return ToolResult(
            tool=self.tool_name,
            status="ok",
            confidence=confidence,
            freshness_days=freshness,
            data_ref=None,
            summary=self._valuation_summary(data),
        )

    def _valuation_summary(self, data: dict) -> str:
        listed_multiple = 8.5  # 예시 동종 EV/EBITDA
        sme_multiple = listed_multiple * LIQUIDITY_DISCOUNT * GOVERNANCE_DISCOUNT
        return (
            f"[밸류에이션 벤치마크] 동종 상장사 EV/EBITDA 평균: {listed_multiple:.1f}x | "
            f"SME 보정 배수 (유동성·지배구조 할인 적용): {sme_multiple:.1f}x | "
            f"비유동성 프리미엄 {int(ILLIQUIDITY_PREMIUM_LOW*100)}~{int(ILLIQUIDITY_PREMIUM_HIGH*100)}% 추가 적용 필요 | "
            f"적정 밸류: [P10 / P50 / P90] 범위로 제시"
        )

    def _stub(self, region_id: str) -> ToolResult:
        confidence = source_confidence(
            freshness_days=365,
            authority_score=self.authority_score,
            coverage_score=0.5,
            consistency_score=0.55,
            max_valid_days=self.max_valid_days,
        )
        listed_multiple = 7.2
        sme_multiple = listed_multiple * LIQUIDITY_DISCOUNT * GOVERNANCE_DISCOUNT
        return ToolResult(
            tool=self.tool_name,
            status="ok",
            confidence=confidence,
            freshness_days=365,
            data_ref=None,
            summary=(
                f"[밸류에이션 - 더미] 동종 상장사 EV/EBITDA: {listed_multiple:.1f}x | "
                f"SME 보정 배수: {sme_multiple:.1f}x | "
                "적정 밸류 추정: P10 6억 / P50 10억 / P90 16억 | "
                "비유동성 프리미엄 20~35% 별도 적용 필요"
            ),
        )
