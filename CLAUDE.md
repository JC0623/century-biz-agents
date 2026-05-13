# OSI-MAS — CLAUDE.md

Open Spatial Intelligence Multi-Agent System.
공공 데이터 기반 입지 분석 및 비즈니스 밸류업 리포트를 생성하는 멀티 에이전트 오픈소스 플랫폼.

---

## 아키텍처 개요

```
Frontend (React + Naver/Kakao Maps)
  ↓ 폴리곤 클릭 이벤트
LangGraph Orchestrator
  ↓ Send API 병렬 팬아웃
MCP Tool Servers (6종)
  ↓ ToolResult 봉투 반환
질 평가 게이트 → 합성 → 스트리밍 리포트
```

### 레이어 구성

| 레이어 | 기술 | 경로 |
|---|---|---|
| Frontend | React, Tailwind, Recharts, ReactFlow | `frontend/` |
| Orchestrator | LangGraph StateGraph | `agents/` |
| MCP Servers | FastAPI (각 도구 독립 서버) | `mcp_servers/` |
| Data Store | PostGIS + Object Storage + Vector DB | `data/` |
| Security (Phase 3) | TEE + ZKP | `secure/` |

---

## 핵심 설계 원칙

### State 관리
- **ToolResult 봉투 패턴** 엄수: 각 MCP 도구는 반드시 `ToolResult` TypedDict 하나만 반환
- 원시 API 페이로드는 **외부 저장소에 저장**, State에는 `data_ref` 포인터만 보관
- 병렬 쓰기가 발생하는 모든 State 키에 **리듀서(reducer)** 적용
- 요약(summary)은 **1~2KB 상한** 유지

```python
class ToolResult(TypedDict):
    tool: str
    status: Literal["ok", "timeout", "error", "skipped"]
    confidence: float        # 0.0 ~ 1.0
    freshness_days: int | None
    data_ref: str | None     # 외부 저장소 포인터
    summary: str             # 2KB 상한
```

### 병렬 실행
- `Send` API로 동적 팬아웃, 리듀서로 팬인
- MCP 도구 타임아웃: **8초** 기본값 — 타임아웃은 예외가 아닌 데이터로 처리
- 최소 2개 도구 성공 시 집계 진행, 미달 시 경고 포함 degraded 응답 반환

### 신뢰도 스코어링
```python
confidence = (
    0.35 * freshness_score   +  # 데이터 최신성
    0.30 * authority_score   +  # 공식 기관 여부
    0.20 * coverage_score    +  # 지역·업종 커버리지
    0.15 * consistency_score    # 타 소스 일치도
)
```

**Fallback 트리거 조건:** `max(confidence) < 0.55` OR `stale_count >= 2`

### Fallback 우선순위 체인
```
1. 공식 공공 API
2. 지자체 포털
3. 지적·용도지역·건물대장
4. 상업 POI / 이동통신 유동인구
5. 뉴스 / 사업자등록 / 웹 검색
6. 사용자 업로드 문서
7. 사용자 직접 확인 요청
```

---

## 에이전트 모듈

### Phase 1 — 기초 분석 (필수 구현)

| 에이전트 | MCP 도구 키 | 주요 데이터 소스 |
|---|---|---|
| 상권 분석 | `tool_market` | 소상공인시장진흥공단 API |
| 공간 가치 | `tool_realestate` | 국토교통부 실거래가 API |
| 산업 클러스터 | `tool_industry` | 전국 공장등록현황 |

### Phase 2 — 전문가 분석

| 에이전트 | MCP 도구 키 | 주요 데이터 소스 |
|---|---|---|
| 밸류에이션 벤치마크 | `tool_valuation` | DART 전자공시, ECOS, 중진공 경영분석 |
| 거시 원가·공급망 | `tool_macro` | 한국은행 ECOS, 물류비 지수 |
| 무형자산·인증 | `tool_ip` | 특허청, 벤처확인시스템 |

---

## LangGraph 그래프 토폴로지

```
START
  → classify_query
  → plan_tools
  → Send(call_mcp_tool) × N      # 병렬 팬아웃
  → normalize_results             # State 압축
  → quality_gate
      → fallback_search           # confidence < 0.55 또는 stale >= 2
      → synthesize                # 충분한 데이터
  → compliance_filter
  → END
```

---

## 시스템 프롬프트 규칙

에이전트 프롬프트 작성 시 반드시 포함할 출력 구조:

```
- 결론
- 신뢰도 (0.00~1.00)
- 데이터 기준일
- 근거
- 한계
- 추가 확인 필요사항
```

**임계값 규칙:**
- 신뢰도 < 0.65 → 추가 검증 권고 명시
- 신뢰도 < 0.45 → 확정적 권고 금지

**신뢰도 표현 패턴 (한국어):**
- ≥ 0.75: "분석 신뢰도 X.XX로 높습니다."
- 0.55~0.74: "신뢰도 X.XX. 방향성 판단 가능하나 별도 확인 권장."
- 0.35~0.54: "신뢰도 X.XX. 투자 전 현장 실사 권장."
- < 0.35: "신뢰 가능한 공개 데이터 불충분."

---

## 밸류에이션 보정 모델

공공 데이터만으로 배수 산출 시 반드시 보정 적용:

```
SME 적정 배수 = 상장사 EV/EBITDA × 유동성할인(0.65) × 지배구조할인(0.85)
비유동성 프리미엄: 20~35% 추가 haircut
결과 표기: 단일 수치 금지 → [P10, P50, P90] 범위 표기
```

**시차 보정:**
```python
adjusted = stale_value * exp(-λ * staleness_days)
# λ = 0.3 (빠른 변화 업종), 0.1 (안정 업종)
```

---

## 프론트엔드 시각화 컴포넌트

| 컴포넌트 | 라이브러리 | 우선순위 |
|---|---|---|
| 폴리곤 히트맵 | Naver/Kakao Maps + GeoJSON | P0 |
| 민감도 토네이도 차트 | `recharts` BarChart (horizontal) | P1 |
| 시나리오 비교 매트릭스 | Custom table + 색상 코딩 | P1 |
| 경쟁력 레이더 차트 | `recharts` RadarChart | P2 |
| 에이전트 추론 DAG | `ReactFlow` | P2 |
| 시계열 스파크라인 | `d3` inline SVG | P3 |
| 리스크-수익 스캐터 | `recharts` ScatterChart | P3 |

모바일: Bottom sheet (에이전트 채팅), Swipeable card (시나리오 비교).

---

## 보안 (Phase 3)

**프라이빗 재무 데이터 결합 시 레이어드 전략:**

| 기술 | 사용 목적 |
|---|---|
| **TEE** | 기본 재무 분석 (Python/SQL/LLM 워크플로우) |
| **ZKP** | 좁은 증명: "부채비율 < 200%", 벤처 자격 확인 |
| **MPC** | SME 간 집계 벤치마크 (개별 값 비공개) |

**키 계층:** `HSM 루트 → 테넌트 마스터 → DEK (원장/문서/파생/감사)`

**컴플라이언스:** ISMS-P(K-ISMS), ISO 27001 — Day 1 설계 적용.

---

## 커밋 규칙

- 커밋 메시지는 **반드시 한국어**로 작성
- 형식: `[동사] [대상]: [설명]` (예: `기능 추가: 상권 분석 에이전트 MCP 연동`)
- 자주 쓰는 동사: `초기 설정`, `기능 추가`, `버그 수정`, `리팩터링`, `문서 업데이트`, `테스트 추가`

---

## 코드 컨벤션

- Python 3.11+, `TypedDict` 적극 활용
- 비동기: `asyncio` 기반, MCP 호출은 항상 `asyncio.wait_for` 래핑
- 에러 처리: 예외를 State의 `status: "error"` 필드로 변환 (그래프 중단 금지)
- 로그: 프라이빗 재무 데이터를 로그·트레이스·프롬프트·체크포인트에 포함 금지
- 테스트: 각 MCP 도구는 타임아웃 및 부분 실패 시나리오 포함

---

## 개발 로드맵

| 주차 | 목표 |
|---|---|
| 1주 | 6대 MCP JSON 스키마, ToolResult 구조, 공공 API 연동 |
| 2주 | LangGraph Send 팬아웃, quality_gate, 신뢰도 스코어링 |
| 3주 | GeoJSON 폴리곤, 토네이도·레이더·DAG 시각화, 모바일 UI |
| 4주 | Fallback 체인, 베이지안 밸류에이션 보정, TEE 아키텍처 설계 |
