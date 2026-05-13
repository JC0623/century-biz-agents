# OSI-MAS — Open Spatial Intelligence Multi-Agent System

> 공공 데이터 기반 입지 분석 및 비즈니스 밸류업 리포트 자동화 플랫폼

파편화된 공공 데이터(상권·부동산·산업·거시경제)를 AI 에이전트가 자율 수집·융합하여, 지도 위 폴리곤 클릭 한 번으로 **데이터 기반 입지 분석 및 기업 밸류업 리포트**를 생성하는 오픈소스 플랫폼입니다.

---

## 주요 기능

| 기능 | 설명 |
|---|---|
| **공간 탐색** | 행정동·산업단지 단위 폴리곤 히트맵으로 데이터 밀집도 시각화 |
| **원클릭 분석** | 폴리곤 선택 시 6개 AI 에이전트 병렬 가동 |
| **밸류에이션 리포트** | EV/EBITDA 벤치마크 + 규모할인 보정 + P10/P50/P90 범위 제시 |
| **신뢰도 명시** | 데이터 최신성·권위성·커버리지 기반 0~1 신뢰도 점수 자동 산출 |
| **스트리밍 리포트** | 에이전트 채팅 패널에 분석 결과 실시간 스트리밍 |
| **고급 시각화** | 민감도 토네이도 차트, 시나리오 매트릭스, 경쟁력 레이더, 에이전트 DAG |

---

## 기술 스택

```
Frontend      React 18 · Tailwind CSS · Recharts · ReactFlow
Maps          Naver Maps API / Kakao Maps API (GeoJSON Polygon)
Orchestration LangGraph (StateGraph + Send API)
Data Protocol MCP (Model Context Protocol) — 6개 독립 API 서버
LLM           Claude Sonnet · GPT-4o (Function Calling)
Storage       PostGIS · Object Storage · Vector DB
Security      TEE · ZKP (Phase 3)
```

---

## 아키텍처

```
사용자 (지도 폴리곤 클릭)
        │
        ▼
┌─────────────────────────┐
│   LangGraph Orchestrator │
│                         │
│  classify → plan_tools  │
│       │                 │
│  Send API (병렬 팬아웃)  │
│  ┌────┴────┐            │
│  ↓    ↓    ↓    ...     │
│ MCP  MCP  MCP  (6종)    │
│  └────┬────┘            │
│  ToolResult 봉투 팬인   │
│       │                 │
│  quality_gate           │
│  ├─ fallback_search     │
│  └─ synthesize          │
└─────────────────────────┘
        │
        ▼
  스트리밍 리포트 (채팅 패널)
```

---

## 에이전트 모듈

### Phase 1 — 기초 분석

| 에이전트 | 역할 | 데이터 소스 |
|---|---|---|
| 상권 분석 (Market Insight) | 업종별 평균 매출·개폐업률·유동인구 | 소상공인시장진흥공단 API |
| 공간 가치 (Real Estate) | 용도지역·면적·인근 실거래가 비교 | 국토교통부 실거래가 API |
| 산업 클러스터 (Industrial) | 반경 내 밀집 업종·물류 인프라 분포 | 전국 공장등록현황 |

### Phase 2 — 전문가 분석

| 에이전트 | 역할 | 데이터 소스 |
|---|---|---|
| 밸류에이션 벤치마크 | EV/EBITDA 배수 보정 및 적정가치 산정 | DART 전자공시 · ECOS · 중진공 |
| 거시 원가·공급망 | 원자재·물류비·전력비 변동성 리스크 | 한국은행 ECOS · 물류비 지수 |
| 무형자산·인증 | 특허·상표·벤처·이노비즈 인증 프리미엄 | 특허청 · 벤처확인시스템 |

---

## 시각화 도구

| 차트 | 목적 | 우선순위 |
|---|---|---|
| 폴리곤 히트맵 | 지역별 데이터 밀집도 공간 탐색 | P0 |
| 민감도 토네이도 차트 | 밸류에이션 민감 변수 즉시 파악 | P1 |
| 시나리오 비교 매트릭스 | Bull/Base/Bear 3가지 케이스 비교 | P1 |
| 경쟁력 레이더 차트 | 8개 축 비즈니스 품질 종합 평가 | P2 |
| 에이전트 추론 DAG | AI 분석 경로 투명 시각화 | P2 |
| 시계열 스파크라인 | 폴리곤 위 월별 매출 추이 오버레이 | P3 |
| 리스크-수익 스캐터 | 대상 vs 유사 사업체 포지셔닝 | P3 |

---

## 신뢰도 시스템

공공 데이터의 한계를 사용자에게 투명하게 전달합니다.

```
신뢰도 = 0.35 × 최신성 + 0.30 × 권위성 + 0.20 × 커버리지 + 0.15 × 일관성
```

| 신뢰도 | 시스템 동작 |
|---|---|
| ≥ 0.75 | 정상 분석 리포트 제공 |
| 0.55~0.74 | 리포트 제공 + 추가 확인 항목 명시 |
| 0.35~0.54 | 방향성만 제시 + 현장 실사 권고 |
| < 0.35 | 자동 Fallback → 보조 데이터 소스 탐색 |

---

## 빠른 시작

### 사전 요구사항

- Python 3.11+
- Node.js 20+
- Docker (PostGIS 실행용)

### 설치

```bash
# 저장소 클론
git clone https://github.com/your-org/osi-mas.git
cd osi-mas

# Python 의존성 설치
pip install -r requirements.txt

# 프론트엔드 의존성 설치
cd frontend && npm install

# 환경 변수 설정
cp .env.example .env
# .env 파일에 아래 키 입력:
#   ANTHROPIC_API_KEY
#   OPENAI_API_KEY
#   NAVER_MAPS_CLIENT_ID (또는 KAKAO_MAPS_APP_KEY)
#   공공데이터포털 API 키
```

### 실행

```bash
# MCP 서버 실행 (6개 병렬)
python -m mcp_servers.start_all

# LangGraph Orchestrator 실행
python -m agents.server

# 프론트엔드 실행
cd frontend && npm run dev
```

브라우저에서 `http://localhost:5173` 접속 → 지도에서 폴리곤 클릭.

---

## 프로젝트 구조

```
osi-mas/
├── agents/                  # LangGraph 오케스트레이터
│   ├── graph.py             # StateGraph 정의 (Send API 팬아웃)
│   ├── state.py             # OSIMASState, ToolResult 스키마
│   ├── nodes/               # 각 그래프 노드
│   └── prompts/             # 에이전트 시스템 프롬프트
├── mcp_servers/             # MCP 도구 서버 (6개)
│   ├── market/              # 상권 분석
│   ├── realestate/          # 공간 가치
│   ├── industry/            # 산업 클러스터
│   ├── valuation/           # 밸류에이션 벤치마크
│   ├── macro/               # 거시 원가·공급망
│   └── ip/                  # 무형자산·인증
├── frontend/                # React 프론트엔드
│   ├── src/
│   │   ├── components/
│   │   │   ├── MapView/     # 폴리곤 히트맵
│   │   │   ├── Charts/      # 토네이도·레이더·DAG 등
│   │   │   └── ChatPanel/   # 에이전트 스트리밍 패널
│   │   └── App.tsx
│   └── package.json
├── data/                    # 데이터 파이프라인
├── CLAUDE.md                # AI 개발 지침
└── README.md
```

---

## 개발 로드맵

- [x] PRD 및 아키텍처 설계 완료
- [ ] **1주차** — 6대 MCP 도구 스키마 정의 및 공공 API 연동
- [ ] **2주차** — LangGraph Send 팬아웃, quality_gate, 신뢰도 스코어링
- [ ] **3주차** — GeoJSON 폴리곤 렌더링, 시각화 컴포넌트 구현
- [ ] **4주차** — Fallback 체인, 베이지안 밸류에이션 보정, 최적화
- [ ] **Phase 3** — TEE 기반 프라이빗 재무 데이터 결합, ISMS-P 인증

---

## 기여 방법

1. 이슈 또는 기능 제안 등록
2. `feature/your-feature` 브랜치 생성
3. 변경사항 커밋 및 PR 생성
4. 리뷰 및 병합

---

## 라이선스

MIT License — 자유롭게 사용, 수정, 배포 가능.
