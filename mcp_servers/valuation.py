"""
밸류에이션 벤치마크 에이전트 — DART 전자공시 + 한국은행 ECOS
동종 업종 EV/EBITDA, 이익률 벤치마크 및 보정 배수 산출
DART API: https://opendart.fss.or.kr/
ECOS API: https://ecos.bok.or.kr/
"""
import math
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

# 비유동성 haircut 범위 — P10(최대), P90(최소)
ILLIQUIDITY_HAIRCUT_HIGH = 0.35  # 비관 시나리오
ILLIQUIDITY_HAIRCUT_LOW  = 0.20  # 낙관 시나리오
ILLIQUIDITY_HAIRCUT_MID  = (ILLIQUIDITY_HAIRCUT_HIGH + ILLIQUIDITY_HAIRCUT_LOW) / 2  # 0.275

# 업종별 기본 EV/EBITDA 배수 (DART 미연동 시 fallback)
SECTOR_MULTIPLES: dict[str, float] = {
    "음식업": 5.5,
    "소매업": 6.0,
    "제조업": 7.5,
    "서비스업": 8.0,
    "IT": 12.0,
    "물류": 6.5,
    "건설": 5.0,
    "기본": 7.0,
}

# 업종 시차 감쇠 계수 λ (CLAUDE.md 명세)
LAMBDA_FAST = 0.3   # 빠른 변화 업종 (음식, 소매)
LAMBDA_SLOW = 0.1   # 안정 업종 (제조, 물류)


def _stale_adjusted(value: float, staleness_days: int, fast_sector: bool) -> float:
    lam = LAMBDA_FAST if fast_sector else LAMBDA_SLOW
    return value * math.exp(-lam * staleness_days / 365)


def _detect_sector(query: str) -> tuple[str, bool]:
    """쿼리 키워드로 업종과 변동성 여부 추정. (sector_name, is_fast_sector)"""
    q = query.lower()
    if any(k in q for k in ["식당", "음식", "카페", "베이커리", "식품"]):
        return "음식업", True
    if any(k in q for k in ["소매", "편의점", "마트", "쇼핑"]):
        return "소매업", True
    if any(k in q for k in ["제조", "공장", "생산"]):
        return "제조업", False
    if any(k in q for k in ["물류", "운송", "창고"]):
        return "물류", False
    if any(k in q for k in ["it", "소프트웨어", "앱", "플랫폼"]):
        return "IT", True
    if any(k in q for k in ["건설", "부동산"]):
        return "건설", False
    return "기본", False


def _percentile_range(
    ebitda_man: float,
    listed_multiple: float,
    fast_sector: bool,
) -> tuple[float, float, float]:
    """
    P10 / P50 / P90 밸류에이션 범위 산출 (단위: 만원).

    적용 순서:
    1. 상장사 배수 → SME 배수 (유동성·지배구조 할인)
    2. 비유동성 haircut: P10=35%, P50=27.5%, P90=20%
    3. 변동성 업종(fast_sector): 분산 ±15% 추가 확대
    """
    sme_multiple = listed_multiple * LIQUIDITY_DISCOUNT * GOVERNANCE_DISCOUNT
    base = ebitda_man * sme_multiple

    p10 = base * (1 - ILLIQUIDITY_HAIRCUT_HIGH)   # 비관
    p50 = base * (1 - ILLIQUIDITY_HAIRCUT_MID)    # 중간
    p90 = base * (1 - ILLIQUIDITY_HAIRCUT_LOW)    # 낙관

    if fast_sector:
        p10 *= 0.85
        p90 *= 1.15

    return round(p10), round(p50), round(p90)


def _fmt_bil(man_won: float) -> str:
    """만원 → '0.0억' 문자열 변환."""
    return f"{man_won / 10_000:.1f}"


class ValuationTool(BaseMCPTool):
    tool_name = "tool_valuation"
    authority_score = 0.75   # DART=공식, 보정 모델=추정 혼합
    max_valid_days = 400     # DART 연간 재무제표 기준 (사업연도 주기)

    async def _fetch(self, region_id: str, query: str) -> ToolResult:
        if not DART_API_KEY:
            return self._stub(region_id, query)

        sector, fast_sector = _detect_sector(query)
        listed_multiple = SECTOR_MULTIPLES.get(sector, SECTOR_MULTIPLES["기본"])

        # 시차 보정 (6개월 기준)
        staleness_days = 180
        adj_multiple = _stale_adjusted(listed_multiple, staleness_days, fast_sector)

        corp_code = "00126380"  # 기본값: 삼성전자 (연동 전 테스트용)
        try:
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

            # 영업이익 (원) → 만원 변환 / 미발견 시 SME 기본값 5억원
            ebitda_man = 50_000  # 5억원 기본 (만원)
            for item in data.get("list", []):
                if item.get("account_nm") == "영업이익":
                    try:
                        won = int(item.get("thstrm_amount", "0").replace(",", ""))
                        ebitda_man = won // 10_000  # 원 → 만원
                        break
                    except (ValueError, TypeError):
                        pass

        except Exception:
            return self._stub(region_id, query)

        p10, p50, p90 = _percentile_range(ebitda_man, adj_multiple, fast_sector)
        freshness = 365

        confidence = source_confidence(
            freshness_days=freshness,
            authority_score=self.authority_score,
            coverage_score=0.60,
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
                f"[밸류에이션 벤치마크] 업종: {sector} | "
                f"상장사 EV/EBITDA: {listed_multiple:.1f}x → 시차 보정 후 {adj_multiple:.2f}x | "
                f"SME 보정 배수: {adj_multiple * LIQUIDITY_DISCOUNT * GOVERNANCE_DISCOUNT:.2f}x | "
                f"적정 밸류: P10 {_fmt_bil(p10)}억 / P50 {_fmt_bil(p50)}억 / P90 {_fmt_bil(p90)}억원 | "
                f"비유동성 haircut {int(ILLIQUIDITY_HAIRCUT_LOW*100)}~{int(ILLIQUIDITY_HAIRCUT_HIGH*100)}% 적용"
            ),
        )

    def _stub(self, region_id: str, query: str = "") -> ToolResult:
        confidence = source_confidence(
            freshness_days=365,
            authority_score=self.authority_score,
            coverage_score=0.5,
            consistency_score=0.55,
            max_valid_days=self.max_valid_days,
        )
        sector, fast_sector = _detect_sector(query)
        listed_multiple = SECTOR_MULTIPLES.get(sector, SECTOR_MULTIPLES["기본"])
        ebitda_man = 30_000  # 더미 EBITDA: 3억원 (만원 단위)
        p10, p50, p90 = _percentile_range(ebitda_man, listed_multiple, fast_sector)

        return ToolResult(
            tool=self.tool_name,
            status="ok",
            confidence=confidence,
            freshness_days=365,
            data_ref=None,
            summary=(
                f"[밸류에이션 - 더미] 업종: {sector} | "
                f"상장사 EV/EBITDA: {listed_multiple:.1f}x | "
                f"SME 보정 배수: {listed_multiple * LIQUIDITY_DISCOUNT * GOVERNANCE_DISCOUNT:.2f}x | "
                f"적정 밸류 추정: P10 {_fmt_bil(p10)}억 / P50 {_fmt_bil(p50)}억 / P90 {_fmt_bil(p90)}억원 | "
                "비유동성 haircut 20~35% 적용"
            ),
        )
