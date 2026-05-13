"""
무형자산·인증 가치 에이전트 — 특허청 + 벤처확인시스템
특허/상표권 보유, 벤처·이노비즈·메인비즈 인증 여부 및 기술 프리미엄 산정
특허청 API: https://www.data.go.kr/data/15084756/openapi.do
벤처확인: https://www.venturein.or.kr/
"""
import os
from agents.state import ToolResult
from agents.confidence import source_confidence
from .base import BaseMCPTool


PUBLIC_DATA_API_KEY = os.getenv("PUBLIC_DATA_API_KEY", "")
KIPRIS_BASE_URL = "http://plus.kipris.or.kr/openapi/rest"


class IPTool(BaseMCPTool):
    tool_name = "tool_ip"
    authority_score = 0.85
    max_valid_days = 365

    async def _fetch(self, region_id: str, query: str) -> ToolResult:
        if not PUBLIC_DATA_API_KEY:
            return self._stub(region_id)

        # 사업자명 또는 지역 기반 특허 검색
        applicant = query.split()[-1] if query else region_id

        resp = await self.client.get(
            f"{KIPRIS_BASE_URL}/patUtiModInfoSearchSevice/applicantNameSearchInfo",
            params={
                "applicant": applicant,
                "accessKey": PUBLIC_DATA_API_KEY,
                "numOfRows": "10",
                "pageNo": "1",
            },
        )
        resp.raise_for_status()
        text = resp.text
        freshness = 180

        patent_count = text.count("<inventionTitle>")
        confidence = source_confidence(
            freshness_days=freshness,
            authority_score=self.authority_score,
            coverage_score=0.65 if patent_count > 0 else 0.3,
            consistency_score=0.7,
            max_valid_days=self.max_valid_days,
        )

        return ToolResult(
            tool=self.tool_name,
            status="ok",
            confidence=confidence,
            freshness_days=freshness,
            data_ref=None,
            summary=(
                f"[무형자산] 특허 검색 결과: {patent_count}건 | "
                f"검색어: {applicant}"
            ),
        )

    def _stub(self, region_id: str) -> ToolResult:
        confidence = source_confidence(
            freshness_days=180,
            authority_score=self.authority_score,
            coverage_score=0.5,
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
                "[무형자산·인증 - 더미] 등록 특허 3건 / 출원 중 2건 | "
                "상표권 1건 (유효) | 벤처기업 인증: 미확인 | "
                "이노비즈 인증: 미확인 | 기술 프리미엄 산정 데이터 부족"
            ),
        )
