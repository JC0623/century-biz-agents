# codex advisor artifact

- Provider: codex
- Exit code: 0
- Created at: 2026-05-13T07:22:20.920Z

## Original task

You are a senior backend architect reviewing a PRD for OSI-MAS (Open Spatial Intelligence Multi-Agent System). Answer these technical questions in detail:

Q1. [LangGraph State Management Bottlenecks] When orchestrating 6 MCP tools via LangGraph, what are the potential bottleneck patterns in inter-agent state passing? Specifically address: (a) shared state schema design for 6 agents with heterogeneous data, (b) fan-out/fan-in parallelism patterns for concurrent API calls, (c) partial failure handling when one MCP tool times out, (d) state size bloat as agents accumulate data, (e) recommended LangGraph node/edge patterns (e.g., Send API, conditional edges) for this use case.

Q4. [Security Architecture for Private Financial Data] After open-source launch, how to safely combine private financial data (accounting books, etc.) with public data? Design a security architecture covering: (a) Zero-Knowledge Proof feasibility for financial ratio computation without revealing raw data, (b) Trusted Execution Environment (TEE) vs ZKP tradeoffs for Korean SME context, (c) federated computation model using MPC (Multi-Party Computation), (d) data residency and encryption-at-rest design, (e) audit trail and compliance (K-ISMS, ISO 27001) considerations.

Q5. [Edge Case System Prompt Strategy] When public data for a region is sparse or stale, what is the optimal system prompt strategy for AI agents to: (a) explicitly communicate data confidence/staleness to users with quantified uncertainty scores, (b) automatically trigger fallback data source exploration, (c) implement a confidence-weighted aggregation model across data sources, (d) specific prompt templates with chain-of-thought for data quality assessment, (e) graceful degradation messaging patterns in Korean business context.

Provide concrete, implementation-ready recommendations with code snippets or pseudocode where applicable.

## Final prompt

You are a senior backend architect reviewing a PRD for OSI-MAS (Open Spatial Intelligence Multi-Agent System). Answer these technical questions in detail:

Q1. [LangGraph State Management Bottlenecks] When orchestrating 6 MCP tools via LangGraph, what are the potential bottleneck patterns in inter-agent state passing? Specifically address: (a) shared state schema design for 6 agents with heterogeneous data, (b) fan-out/fan-in parallelism patterns for concurrent API calls, (c) partial failure handling when one MCP tool times out, (d) state size bloat as agents accumulate data, (e) recommended LangGraph node/edge patterns (e.g., Send API, conditional edges) for this use case.

Q4. [Security Architecture for Private Financial Data] After open-source launch, how to safely combine private financial data (accounting books, etc.) with public data? Design a security architecture covering: (a) Zero-Knowledge Proof feasibility for financial ratio computation without revealing raw data, (b) Trusted Execution Environment (TEE) vs ZKP tradeoffs for Korean SME context, (c) federated computation model using MPC (Multi-Party Computation), (d) data residency and encryption-at-rest design, (e) audit trail and compliance (K-ISMS, ISO 27001) considerations.

Q5. [Edge Case System Prompt Strategy] When public data for a region is sparse or stale, what is the optimal system prompt strategy for AI agents to: (a) explicitly communicate data confidence/staleness to users with quantified uncertainty scores, (b) automatically trigger fallback data source exploration, (c) implement a confidence-weighted aggregation model across data sources, (d) specific prompt templates with chain-of-thought for data quality assessment, (e) graceful degradation messaging patterns in Korean business context.

Provide concrete, implementation-ready recommendations with code snippets or pseudocode where applicable.

## Raw output

```text
## Q1. LangGraph State Management Bottlenecks

Primary bottleneck: treating “agent state” as a shared mutable document. For 6 heterogeneous MCP tools, design the graph as a map-reduce pipeline with typed partial outputs, reducers, and external artifact storage.

### 1. Shared State Schema

Use a thin global state plus typed tool result envelopes. Do not let each agent write arbitrary keys.

```python
from typing import Annotated, Literal, TypedDict, NotRequired
from operator import add
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

ToolName = Literal[
    "cadastre", "poi", "traffic", "finance", "news", "demographics"
]

class ToolResult(TypedDict):
    tool: ToolName
    request_id: str
    status: Literal["ok", "timeout", "error", "skipped"]
    confidence: float
    freshness_days: int | None
    data_ref: str | None       # object-store/vector-db pointer
    summary: str
    error: NotRequired[str]

def merge_results(left: dict[str, ToolResult], right: dict[str, ToolResult]):
    return {**left, **right}

class OSIMASState(TypedDict):
    query: str
    region_id: str
    requested_tools: list[ToolName]
    tool_results: Annotated[dict[str, ToolResult], merge_results]
    warnings: Annotated[list[str], add]
    final_answer: NotRequired[str]
```

Recommended rules:

- Global state contains only routing inputs, normalized summaries, confidence metadata, and references.
- Raw MCP responses go to blob storage, PostGIS, object storage, or vector DB.
- Each MCP tool returns one `ToolResult` envelope.
- Use reducers for any key written by multiple parallel nodes.
- Avoid one giant `messages` list as the canonical state for everything.

### 2. Fan-Out / Fan-In Pattern

Use LangGraph `Send` for dynamic fan-out. Each MCP call receives a narrow state slice, then writes back to the reducer-backed `tool_results`.

```python
def route_tools(state: OSIMASState):
    return [
        Send("call_mcp_tool", {
            "tool": tool,
            "query": state["query"],
            "region_id": state["region_id"],
        })
        for tool in state["requested_tools"]
    ]

async def call_mcp_tool(state):
    tool = state["tool"]
    result = await invoke_mcp_with_timeout(tool, state)
    return {
        "tool_results": {
            result["tool"]: result
        }
    }

builder = StateGraph(OSIMASState)
builder.add_node("plan", plan_tools)
builder.add_node("call_mcp_tool", call_mcp_tool)
builder.add_node("aggregate", aggregate_results)

builder.add_edge(START, "plan")
builder.add_conditional_edges("plan", route_tools)
builder.add_edge("call_mcp_tool", "aggregate")
builder.add_edge("aggregate", END)
```

This gives you map-reduce behavior: dynamic tool selection, concurrent calls, deterministic aggregation.

### 3. Partial Failure Handling

A timeout should be data, not an exception that kills the whole graph.

```python
import asyncio, time

async def invoke_mcp_with_timeout(tool: ToolName, state, timeout_s=8) -> ToolResult:
    started = time.time()
    try:
        payload = await asyncio.wait_for(
            MCP_CLIENTS[tool].call(region_id=state["region_id"], query=state["query"]),
            timeout=timeout_s,
        )
        ref = await persist_raw_payload(tool, payload)
        return {
            "tool": tool,
            "request_id": make_request_id(),
            "status": "ok",
            "confidence": score_payload_quality(payload),
            "freshness_days": estimate_freshness(payload),
            "data_ref": ref,
            "summary": summarize_payload(payload),
        }
    except asyncio.TimeoutError:
        return {
            "tool": tool,
            "request_id": make_request_id(),
            "status": "timeout",
            "confidence": 0.0,
            "freshness_days": None,
            "data_ref": None,
            "summary": "",
            "error": f"{tool} timed out after {timeout_s}s",
        }
```

Aggregation should proceed when at least the minimum viable evidence set exists:

```python
def aggregate_results(state: OSIMASState):
    results = state["tool_results"]
    ok = [r for r in results.values() if r["status"] == "ok"]

    if len(ok) < 2:
        return {
            "warnings": ["사용 가능한 공공데이터가 부족하여 분석 신뢰도가 낮습니다."],
            "final_answer": degraded_answer(results),
        }

    return {
        "final_answer": synthesize_weighted_answer(ok),
    }
```

### 4. State Size Bloat

Expected bloat sources:

- raw API payloads copied into state
- long agent messages accumulating across nodes
- repeated geospatial features, polygons, POI lists
- large financial/accounting tables
- checkpoint persistence of oversized state

Mitigation:

- Store raw data externally; keep `data_ref`.
- Normalize every tool response into a small envelope.
- Keep summaries bounded, e.g. 1 to 2 KB per tool.
- Use confidence/freshness/source metadata instead of full documents.
- Add a compaction node after fan-in.
- Use subgraphs for tool-specific state so private intermediate fields do not leak into the global state.

Recommended topology:

```text
START
  -> classify_query
  -> plan_tools
  -> Send(call_mcp_tool) x N
  -> normalize_results
  -> quality_gate
      -> fallback_search, if sparse/stale
      -> synthesize, if sufficient
  -> compliance_filter
  -> END
```

Use conditional edges for routing, `Send` for parallel tool calls, reducers for fan-in, and `Command` only when a node must both update state and choose the next node.

---

## Q4. Security Architecture for Private Financial Data

The architecture should separate public OSI data from private SME financial data by default, then combine them only inside controlled computation boundaries.

### 1. ZKP Feasibility

ZKP is feasible for narrow financial attestations, not general analytics.

Good ZKP use cases:

- “Debt-to-equity ratio is below 200%”
- “Current ratio is above 1.2”
- “Revenue is within an SME eligibility band”
- “This submitted balance sheet hashes to an auditor-signed commitment”

Poor ZKP use cases:

- free-form agentic analysis over ledger rows
- exploratory financial diagnostics
- arbitrary SQL over accounting books
- LLM reasoning directly over private documents

Pattern:

```text
private books -> canonical ledger -> commitment hash
              -> ratio circuit -> proof
public verifier receives:
  - proof
  - public threshold
  - committed statement id
  - pass/fail or bounded range
```

ZKP should be an attestation layer, not the main analytics runtime.

### 2. TEE vs ZKP for Korean SMEs

For Korean SMEs, I would use TEEs first, ZKP selectively.

| Option | Strength | Weakness | Recommendation |
|---|---|---|---|
| TEE | Practical for existing Python/SQL/LLM workflows | Requires trust in cloud/hardware attestation | Best default for private financial analysis |
| ZKP | Strong cryptographic privacy for fixed claims | Expensive circuit engineering, limited flexibility | Use for ratios, eligibility, audit attestations |
| MPC | Strong cross-party privacy | Operationally complex, latency-heavy | Use for federation/benchmarking, not single-SME analysis |

TEE architecture:

```text
tenant KMS key
  -> encrypted ledger storage
  -> attested enclave job
  -> decrypt inside enclave only
  -> compute ratios/features
  -> emit minimal derived metrics
  -> destroy plaintext workspace
```

Use remote attestation before releasing data keys:

```python
def release_data_key(attestation_doc, tenant_id, job_policy):
    assert verify_tee_attestation(attestation_doc)
    assert attestation_doc.measurement in APPROVED_IMAGES
    assert job_policy.allows("financial_ratio_compute")
    return kms.decrypt_data_key(tenant_id)
```

### 3. Federated MPC Model

Use MPC when multiple SMEs, lenders, or regional entities jointly compute benchmarks without exposing raw books.

Example: regional liquidity benchmark.

```text
SME A current_ratio -> secret shares -> MPC nodes
SME B current_ratio -> secret shares -> MPC nodes
SME C current_ratio -> secret shares -> MPC nodes

MPC output:
  - median current ratio by industry/region
  - percentile bucket for each participant
  - no raw participant values
```

Implementation model:

```python
class FederatedMetricJob(TypedDict):
    metric: str                 # "current_ratio"
    cohort: dict                # region, industry, revenue band
    min_participants: int       # e.g. k >= 20
    privacy_budget: float | None
    output_policy: str          # aggregate_only
```

Guardrails:

- minimum cohort size, e.g. k-anonymity threshold
- no single-company output
- no repeated differencing attacks
- rate limits on near-identical cohort queries
- optional differential privacy noise for public dashboards

### 4. Residency and Encryption at Rest

Recommended Korean SME deployment:

- Primary data region: Korea-based cloud region where possible.
- Tenant-isolated storage buckets and databases.
- Per-tenant envelope encryption.
- KMS/HSM-backed key hierarchy.
- Separate public-data lake from private financial-data vault.
- No raw financial data in logs, traces, prompts, or LangGraph checkpoints.
- Private data retention policy by tenant contract.
- Cross-border transfer disabled unless explicitly contracted and legally reviewed.

Key layout:

```text
root HSM key
  -> tenant master key
      -> ledger data encryption key
      -> document data encryption key
      -> derived feature data key
      -> audit log signing key
```

### 5. Audit Trail and Compliance

Design for ISMS-P / K-ISMS and ISO 27001 from day one.

Audit events:

```json
{
  "event_id": "evt_...",
  "tenant_id": "t_123",
  "actor": "user:456",
  "purpose": "credit_analysis",
  "data_class": "private_financial",
  "operation": "compute_current_ratio",
  "input_refs": ["ledger_commitment:abc"],
  "output_refs": ["metric:def"],
  "model_version": "osi-mas-2026-05",
  "policy_version": "fin-policy-v3",
  "timestamp": "2026-05-13T10:15:00+09:00",
  "result": "success"
}
```

Controls to implement:

- purpose-based access control
- tenant RBAC/ABAC
- break-glass access with dual approval
- immutable append-only audit logs
- signed audit log chains
- quarterly access review
- vendor/subprocessor register
- incident response runbooks
- DPIA/PIA for personal information
- secure SDLC, threat modeling, dependency scanning
- backup encryption and restore testing

---

## Q5. Edge Case System Prompt Strategy

Do not let agents hide weak evidence. Make data quality a first-class output field.

### 1. Confidence and Staleness

Use structured quality scoring:

```python
def source_confidence(source):
    freshness = max(0, 1 - source.freshness_days / source.max_valid_days)
    authority = source.authority_score          # official registry > blog
    coverage = source.coverage_score            # region/sample completeness
    consistency = source.consistency_score      # agreement with other sources

    return round(
        0.35 * freshness +
        0.30 * authority +
        0.20 * coverage +
        0.15 * consistency,
        3,
    )
```

Output contract:

```json
{
  "claim": "해당 상권의 유동인구는 증가 추세입니다.",
  "confidence": 0.62,
  "staleness_days": 420,
  "evidence_count": 3,
  "limitations": [
    "가장 최근 공공 유동인구 데이터가 2025년 3월 기준입니다.",
    "읍면동 단위 데이터만 있어 필지 단위 추정 오차가 있습니다."
  ]
}
```

### 2. Fallback Source Exploration

Trigger fallback when confidence is low, data is stale, or source disagreement is high.

```python
def should_fallback(state):
    scores = [r["confidence"] for r in state["tool_results"].values()]
    stale = [r for r in state["tool_results"].values()
             if r["freshness_days"] and r["freshness_days"] > 365]

    if not scores:
        return "fallback_search"
    if max(scores) < 0.55:
        return "fallback_search"
    if len(stale) >= 2:
        return "fallback_search"
    return "synthesize"

builder.add_conditional_edges(
    "quality_gate",
    should_fallback,
    {
        "fallback_search": "fallback_search",
        "synthesize": "synthesize",
    },
)
```

Fallback order for OSI-MAS:

```text
1. official public APIs
2. local government portals
3. cadastral / zoning / building registry
4. commercial POI or mobility providers
5. news / business registry / web search
6. user-uploaded documents
7. ask user for confirmation
```

### 3. Confidence-Weighted Aggregation

```python
def aggregate_claim(claims):
    weighted = {}

    for c in claims:
        key = c.normalized_claim
        weight = (
            c.confidence *
            c.source_authority *
            max(0.2, 1 - c.freshness_days / 730)
        )
        weighted.setdefault(key, 0)
        weighted[key] += weight

    best_claim = max(weighted.items(), key=lambda x: x[1])
    total = sum(weighted.values())

    return {
        "claim": best_claim[0],
        "confidence": round(best_claim[1] / total, 3),
        "alternatives": weighted,
    }
```

Also track disagreement explicitly:

```python
if top_claim_confidence < 0.6:
    limitations.append("자료 간 결론이 일치하지 않아 보수적으로 해석해야 합니다.")
```

### 4. Prompt Template

Do not ask the model to expose chain-of-thought. Use a private reasoning rubric and require a concise rationale.

```text
System:
You are an OSI-MAS spatial-business analyst.
You must separate facts, estimates, assumptions, and recommendations.
Never present stale or sparse data as certain.
Use Korean business communication style: direct, conservative, and decision-oriented.

Data quality rubric:
- freshness: how old is the data?
- authority: is the source official, commercial, inferred, or user-provided?
- coverage: does it cover the exact region and business category?
- consistency: do independent sources agree?
- actionability: is the evidence strong enough for a business decision?

Instructions:
1. Calculate a confidence score from 0.00 to 1.00.
2. State the newest source date and oldest source date.
3. If confidence < 0.65, recommend additional verification.
4. If confidence < 0.45, avoid firm recommendations.
5. Provide only a concise rationale, not hidden reasoning steps.

Output:
- 결론
- 신뢰도
- 데이터 기준일
- 근거
- 한계
- 추가 확인 필요사항
```

### 5. Korean Graceful Degradation Patterns

High confidence:

```text
분석 신뢰도는 0.82로 높습니다. 2026년 1분기 공공데이터와 최근 상권 지표가 일관되게 같은 방향을 보입니다.
```

Medium confidence:

```text
분석 신뢰도는 0.61입니다. 방향성 판단은 가능하지만, 일부 데이터가 12개월 이상 경과하여 임대료나 유동인구의 최근 변동은 별도 확인이 필요합니다.
```

Low confidence:

```text
현재 데이터만으로는 입지 판단을 확정하기 어렵습니다. 분석 신뢰도는 0.38이며, 해당 지역의 최신 유동인구 및 업종별 매출 데이터가 부족합니다. 임대차 계약이나 투자 판단 전 현장 실사와 카드매출 자료 확인을 권장합니다.
```

No data:

```text
해당 지역에 대해 신뢰 가능한 공개 데이터가 충분하지 않습니다. 추정 분석은 제공할 수 있으나 사업성 판단 근거로 사용하기에는 제한이 큽니다.
```

## Source Notes

LangGraph recommendations are based on current LangGraph docs for `StateGraph`, reducers, conditional edges, and `Send`: [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api), [Send reference](https://reference.langchain.com/python/langgraph/types/Send).  
Security architecture references: NIST privacy-enhancing cryptography overview for ZKP/MPC concepts: [NIST PEC](https://csrc.nist.gov/Projects/pec), [NIST PEC tools](https://csrc.nist.gov/projects/pec/pec-tools); TEE definition from Microsoft confidential computing docs: [TEE](https://learn.microsoft.com/mt-mt/azure/confidential-computing/trusted-execution-environment).  
Korean compliance references: KISA ISMS-P scope/control categories: [ISMS-P overview](https://isms.kisa.or.kr/sysm/intro/selectSysmCertDetail.do), [ISMS-P certification process](https://isms.kisa.or.kr/cert/aply/selectCertPrcdDetail.do); ISO 27001 overview: [ISO/IEC 27001](https://www.iso.org/standard/27001).


OpenAI Codex v0.130.0
--------
workdir: c:\Users\next0\claude-test\century-biz-agents
model: gpt-5.5
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: none
reasoning summaries: none
session id: 019e2035-5019-7d53-9229-1e8e635f58b9
--------
user
You are a senior backend architect reviewing a PRD for OSI-MAS (Open Spatial Intelligence Multi-Agent System). Answer these technical questions in detail:

Q1. [LangGraph State Management Bottlenecks] When orchestrating 6 MCP tools via LangGraph, what are the potential bottleneck patterns in inter-agent state passing? Specifically address: (a) shared state schema design for 6 agents with heterogeneous data, (b) fan-out/fan-in parallelism patterns for concurrent API calls, (c) partial failure handling when one MCP tool times out, (d) state size bloat as agents accumulate data, (e) recommended LangGraph node/edge patterns (e.g., Send API, conditional edges) for this use case.

Q4. [Security Architecture for Private Financial Data] After open-source launch, how to safely combine private financial data (accounting books, etc.) with public data? Design a security architecture covering: (a) Zero-Knowledge Proof feasibility for financial ratio computation without revealing raw data, (b) Trusted Execution Environment (TEE) vs ZKP tradeoffs for Korean SME context, (c) federated computation model using MPC (Multi-Party Computation), (d) data residency and encryption-at-rest design, (e) audit trail and compliance (K-ISMS, ISO 27001) considerations.

Q5. [Edge Case System Prompt Strategy] When public data for a region is sparse or stale, what is the optimal system prompt strategy for AI agents to: (a) explicitly communicate data confidence/staleness to users with quantified uncertainty scores, (b) automatically trigger fallback data source exploration, (c) implement a confidence-weighted aggregation model across data sources, (d) specific prompt templates with chain-of-thought for data quality assessment, (e) graceful degradation messaging patterns in Korean business context.

Provide concrete, implementation-ready recommendations with code snippets or pseudocode where applicable.
codex
I’ll verify the current LangGraph orchestration primitives and compliance/security references before giving recommendations, since both APIs and Korean security requirements shift over time.
web search: 
web search: LangGraph Send API conditional edges state reducers official docs
web search: 
web search: site:kisa.or.kr ISMS-P certification control items encryption audit logs Korea official
web search: 
web search: NIST confidential computing trusted execution environment data in use official
codex
## Q1. LangGraph State Management Bottlenecks

Primary bottleneck: treating “agent state” as a shared mutable document. For 6 heterogeneous MCP tools, design the graph as a map-reduce pipeline with typed partial outputs, reducers, and external artifact storage.

### 1. Shared State Schema

Use a thin global state plus typed tool result envelopes. Do not let each agent write arbitrary keys.

```python
from typing import Annotated, Literal, TypedDict, NotRequired
from operator import add
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

ToolName = Literal[
    "cadastre", "poi", "traffic", "finance", "news", "demographics"
]

class ToolResult(TypedDict):
    tool: ToolName
    request_id: str
    status: Literal["ok", "timeout", "error", "skipped"]
    confidence: float
    freshness_days: int | None
    data_ref: str | None       # object-store/vector-db pointer
    summary: str
    error: NotRequired[str]

def merge_results(left: dict[str, ToolResult], right: dict[str, ToolResult]):
    return {**left, **right}

class OSIMASState(TypedDict):
    query: str
    region_id: str
    requested_tools: list[ToolName]
    tool_results: Annotated[dict[str, ToolResult], merge_results]
    warnings: Annotated[list[str], add]
    final_answer: NotRequired[str]
```

Recommended rules:

- Global state contains only routing inputs, normalized summaries, confidence metadata, and references.
- Raw MCP responses go to blob storage, PostGIS, object storage, or vector DB.
- Each MCP tool returns one `ToolResult` envelope.
- Use reducers for any key written by multiple parallel nodes.
- Avoid one giant `messages` list as the canonical state for everything.

### 2. Fan-Out / Fan-In Pattern

Use LangGraph `Send` for dynamic fan-out. Each MCP call receives a narrow state slice, then writes back to the reducer-backed `tool_results`.

```python
def route_tools(state: OSIMASState):
    return [
        Send("call_mcp_tool", {
            "tool": tool,
            "query": state["query"],
            "region_id": state["region_id"],
        })
        for tool in state["requested_tools"]
    ]

async def call_mcp_tool(state):
    tool = state["tool"]
    result = await invoke_mcp_with_timeout(tool, state)
    return {
        "tool_results": {
            result["tool"]: result
        }
    }

builder = StateGraph(OSIMASState)
builder.add_node("plan", plan_tools)
builder.add_node("call_mcp_tool", call_mcp_tool)
builder.add_node("aggregate", aggregate_results)

builder.add_edge(START, "plan")
builder.add_conditional_edges("plan", route_tools)
builder.add_edge("call_mcp_tool", "aggregate")
builder.add_edge("aggregate", END)
```

This gives you map-reduce behavior: dynamic tool selection, concurrent calls, deterministic aggregation.

### 3. Partial Failure Handling

A timeout should be data, not an exception that kills the whole graph.

```python
import asyncio, time

async def invoke_mcp_with_timeout(tool: ToolName, state, timeout_s=8) -> ToolResult:
    started = time.time()
    try:
        payload = await asyncio.wait_for(
            MCP_CLIENTS[tool].call(region_id=state["region_id"], query=state["query"]),
            timeout=timeout_s,
        )
        ref = await persist_raw_payload(tool, payload)
        return {
            "tool": tool,
            "request_id": make_request_id(),
            "status": "ok",
            "confidence": score_payload_quality(payload),
            "freshness_days": estimate_freshness(payload),
            "data_ref": ref,
            "summary": summarize_payload(payload),
        }
    except asyncio.TimeoutError:
        return {
            "tool": tool,
            "request_id": make_request_id(),
            "status": "timeout",
            "confidence": 0.0,
            "freshness_days": None,
            "data_ref": None,
            "summary": "",
            "error": f"{tool} timed out after {timeout_s}s",
        }
```

Aggregation should proceed when at least the minimum viable evidence set exists:

```python
def aggregate_results(state: OSIMASState):
    results = state["tool_results"]
    ok = [r for r in results.values() if r["status"] == "ok"]

    if len(ok) < 2:
        return {
            "warnings": ["사용 가능한 공공데이터가 부족하여 분석 신뢰도가 낮습니다."],
            "final_answer": degraded_answer(results),
        }

    return {
        "final_answer": synthesize_weighted_answer(ok),
    }
```

### 4. State Size Bloat

Expected bloat sources:

- raw API payloads copied into state
- long agent messages accumulating across nodes
- repeated geospatial features, polygons, POI lists
- large financial/accounting tables
- checkpoint persistence of oversized state

Mitigation:

- Store raw data externally; keep `data_ref`.
- Normalize every tool response into a small envelope.
- Keep summaries bounded, e.g. 1 to 2 KB per tool.
- Use confidence/freshness/source metadata instead of full documents.
- Add a compaction node after fan-in.
- Use subgraphs for tool-specific state so private intermediate fields do not leak into the global state.

Recommended topology:

```text
START
  -> classify_query
  -> plan_tools
  -> Send(call_mcp_tool) x N
  -> normalize_results
  -> quality_gate
      -> fallback_search, if sparse/stale
      -> synthesize, if sufficient
  -> compliance_filter
  -> END
```

Use conditional edges for routing, `Send` for parallel tool calls, reducers for fan-in, and `Command` only when a node must both update state and choose the next node.

---

## Q4. Security Architecture for Private Financial Data

The architecture should separate public OSI data from private SME financial data by default, then combine them only inside controlled computation boundaries.

### 1. ZKP Feasibility

ZKP is feasible for narrow financial attestations, not general analytics.

Good ZKP use cases:

- “Debt-to-equity ratio is below 200%”
- “Current ratio is above 1.2”
- “Revenue is within an SME eligibility band”
- “This submitted balance sheet hashes to an auditor-signed commitment”

Poor ZKP use cases:

- free-form agentic analysis over ledger rows
- exploratory financial diagnostics
- arbitrary SQL over accounting books
- LLM reasoning directly over private documents

Pattern:

```text
private books -> canonical ledger -> commitment hash
              -> ratio circuit -> proof
public verifier receives:
  - proof
  - public threshold
  - committed statement id
  - pass/fail or bounded range
```

ZKP should be an attestation layer, not the main analytics runtime.

### 2. TEE vs ZKP for Korean SMEs

For Korean SMEs, I would use TEEs first, ZKP selectively.

| Option | Strength | Weakness | Recommendation |
|---|---|---|---|
| TEE | Practical for existing Python/SQL/LLM workflows | Requires trust in cloud/hardware attestation | Best default for private financial analysis |
| ZKP | Strong cryptographic privacy for fixed claims | Expensive circuit engineering, limited flexibility | Use for ratios, eligibility, audit attestations |
| MPC | Strong cross-party privacy | Operationally complex, latency-heavy | Use for federation/benchmarking, not single-SME analysis |

TEE architecture:

```text
tenant KMS key
  -> encrypted ledger storage
  -> attested enclave job
  -> decrypt inside enclave only
  -> compute ratios/features
  -> emit minimal derived metrics
  -> destroy plaintext workspace
```

Use remote attestation before releasing data keys:

```python
def release_data_key(attestation_doc, tenant_id, job_policy):
    assert verify_tee_attestation(attestation_doc)
    assert attestation_doc.measurement in APPROVED_IMAGES
    assert job_policy.allows("financial_ratio_compute")
    return kms.decrypt_data_key(tenant_id)
```

### 3. Federated MPC Model

Use MPC when multiple SMEs, lenders, or regional entities jointly compute benchmarks without exposing raw books.

Example: regional liquidity benchmark.

```text
SME A current_ratio -> secret shares -> MPC nodes
SME B current_ratio -> secret shares -> MPC nodes
SME C current_ratio -> secret shares -> MPC nodes

MPC output:
  - median current ratio by industry/region
  - percentile bucket for each participant
  - no raw participant values
```

Implementation model:

```python
class FederatedMetricJob(TypedDict):
    metric: str                 # "current_ratio"
    cohort: dict                # region, industry, revenue band
    min_participants: int       # e.g. k >= 20
    privacy_budget: float | None
    output_policy: str          # aggregate_only
```

Guardrails:

- minimum cohort size, e.g. k-anonymity threshold
- no single-company output
- no repeated differencing attacks
- rate limits on near-identical cohort queries
- optional differential privacy noise for public dashboards

### 4. Residency and Encryption at Rest

Recommended Korean SME deployment:

- Primary data region: Korea-based cloud region where possible.
- Tenant-isolated storage buckets and databases.
- Per-tenant envelope encryption.
- KMS/HSM-backed key hierarchy.
- Separate public-data lake from private financial-data vault.
- No raw financial data in logs, traces, prompts, or LangGraph checkpoints.
- Private data retention policy by tenant contract.
- Cross-border transfer disabled unless explicitly contracted and legally reviewed.

Key layout:

```text
root HSM key
  -> tenant master key
      -> ledger data encryption key
      -> document data encryption key
      -> derived feature data key
      -> audit log signing key
```

### 5. Audit Trail and Compliance

Design for ISMS-P / K-ISMS and ISO 27001 from day one.

Audit events:

```json
{
  "event_id": "evt_...",
  "tenant_id": "t_123",
  "actor": "user:456",
  "purpose": "credit_analysis",
  "data_class": "private_financial",
  "operation": "compute_current_ratio",
  "input_refs": ["ledger_commitment:abc"],
  "output_refs": ["metric:def"],
  "model_version": "osi-mas-2026-05",
  "policy_version": "fin-policy-v3",
  "timestamp": "2026-05-13T10:15:00+09:00",
  "result": "success"
}
```

Controls to implement:

- purpose-based access control
- tenant RBAC/ABAC
- break-glass access with dual approval
- immutable append-only audit logs
- signed audit log chains
- quarterly access review
- vendor/subprocessor register
- incident response runbooks
- DPIA/PIA for personal information
- secure SDLC, threat modeling, dependency scanning
- backup encryption and restore testing

---

## Q5. Edge Case System Prompt Strategy

Do not let agents hide weak evidence. Make data quality a first-class output field.

### 1. Confidence and Staleness

Use structured quality scoring:

```python
def source_confidence(source):
    freshness = max(0, 1 - source.freshness_days / source.max_valid_days)
    authority = source.authority_score          # official registry > blog
    coverage = source.coverage_score            # region/sample completeness
    consistency = source.consistency_score      # agreement with other sources

    return round(
        0.35 * freshness +
        0.30 * authority +
        0.20 * coverage +
        0.15 * consistency,
        3,
    )
```

Output contract:

```json
{
  "claim": "해당 상권의 유동인구는 증가 추세입니다.",
  "confidence": 0.62,
  "staleness_days": 420,
  "evidence_count": 3,
  "limitations": [
    "가장 최근 공공 유동인구 데이터가 2025년 3월 기준입니다.",
    "읍면동 단위 데이터만 있어 필지 단위 추정 오차가 있습니다."
  ]
}
```

### 2. Fallback Source Exploration

Trigger fallback when confidence is low, data is stale, or source disagreement is high.

```python
def should_fallback(state):
    scores = [r["confidence"] for r in state["tool_results"].values()]
    stale = [r for r in state["tool_results"].values()
             if r["freshness_days"] and r["freshness_days"] > 365]

    if not scores:
        return "fallback_search"
    if max(scores) < 0.55:
        return "fallback_search"
    if len(stale) >= 2:
        return "fallback_search"
    return "synthesize"

builder.add_conditional_edges(
    "quality_gate",
    should_fallback,
    {
        "fallback_search": "fallback_search",
        "synthesize": "synthesize",
    },
)
```

Fallback order for OSI-MAS:

```text
1. official public APIs
2. local government portals
3. cadastral / zoning / building registry
4. commercial POI or mobility providers
5. news / business registry / web search
6. user-uploaded documents
7. ask user for confirmation
```

### 3. Confidence-Weighted Aggregation

```python
def aggregate_claim(claims):
    weighted = {}

    for c in claims:
        key = c.normalized_claim
        weight = (
            c.confidence *
            c.source_authority *
            max(0.2, 1 - c.freshness_days / 730)
        )
        weighted.setdefault(key, 0)
        weighted[key] += weight

    best_claim = max(weighted.items(), key=lambda x: x[1])
    total = sum(weighted.values())

    return {
        "claim": best_claim[0],
        "confidence": round(best_claim[1] / total, 3),
        "alternatives": weighted,
    }
```

Also track disagreement explicitly:

```python
if top_claim_confidence < 0.6:
    limitations.append("자료 간 결론이 일치하지 않아 보수적으로 해석해야 합니다.")
```

### 4. Prompt Template

Do not ask the model to expose chain-of-thought. Use a private reasoning rubric and require a concise rationale.

```text
System:
You are an OSI-MAS spatial-business analyst.
You must separate facts, estimates, assumptions, and recommendations.
Never present stale or sparse data as certain.
Use Korean business communication style: direct, conservative, and decision-oriented.

Data quality rubric:
- freshness: how old is the data?
- authority: is the source official, commercial, inferred, or user-provided?
- coverage: does it cover the exact region and business category?
- consistency: do independent sources agree?
- actionability: is the evidence strong enough for a business decision?

Instructions:
1. Calculate a confidence score from 0.00 to 1.00.
2. State the newest source date and oldest source date.
3. If confidence < 0.65, recommend additional verification.
4. If confidence < 0.45, avoid firm recommendations.
5. Provide only a concise rationale, not hidden reasoning steps.

Output:
- 결론
- 신뢰도
- 데이터 기준일
- 근거
- 한계
- 추가 확인 필요사항
```

### 5. Korean Graceful Degradation Patterns

High confidence:

```text
분석 신뢰도는 0.82로 높습니다. 2026년 1분기 공공데이터와 최근 상권 지표가 일관되게 같은 방향을 보입니다.
```

Medium confidence:

```text
분석 신뢰도는 0.61입니다. 방향성 판단은 가능하지만, 일부 데이터가 12개월 이상 경과하여 임대료나 유동인구의 최근 변동은 별도 확인이 필요합니다.
```

Low confidence:

```text
현재 데이터만으로는 입지 판단을 확정하기 어렵습니다. 분석 신뢰도는 0.38이며, 해당 지역의 최신 유동인구 및 업종별 매출 데이터가 부족합니다. 임대차 계약이나 투자 판단 전 현장 실사와 카드매출 자료 확인을 권장합니다.
```

No data:

```text
해당 지역에 대해 신뢰 가능한 공개 데이터가 충분하지 않습니다. 추정 분석은 제공할 수 있으나 사업성 판단 근거로 사용하기에는 제한이 큽니다.
```

## Source Notes

LangGraph recommendations are based on current LangGraph docs for `StateGraph`, reducers, conditional edges, and `Send`: [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api), [Send reference](https://reference.langchain.com/python/langgraph/types/Send).  
Security architecture references: NIST privacy-enhancing cryptography overview for ZKP/MPC concepts: [NIST PEC](https://csrc.nist.gov/Projects/pec), [NIST PEC tools](https://csrc.nist.gov/projects/pec/pec-tools); TEE definition from Microsoft confidential computing docs: [TEE](https://learn.microsoft.com/mt-mt/azure/confidential-computing/trusted-execution-environment).  
Korean compliance references: KISA ISMS-P scope/control categories: [ISMS-P overview](https://isms.kisa.or.kr/sysm/intro/selectSysmCertDetail.do), [ISMS-P certification process](https://isms.kisa.or.kr/cert/aply/selectCertPrcdDetail.do); ISO 27001 overview: [ISO/IEC 27001](https://www.iso.org/standard/27001).
tokens used
20,458

```

## Concise summary

Provider completed successfully. Review the raw output for details.

## Action items

- Review the response and extract decisions you want to apply.
- Capture follow-up implementation tasks if needed.
