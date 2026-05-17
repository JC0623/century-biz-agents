"""
OSI-MAS FastAPI 웹 인터페이스
실행: uvicorn api.server:app --reload --port 8000
"""
import asyncio
import json
import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from agents.graph import graph
from api.models import (
    AnalysisRequest,
    AnalysisResponse,
    HealthResponse,
    ToolResultResponse,
)

load_dotenv()

app = FastAPI(
    title="OSI-MAS API",
    description="공공 데이터 기반 입지 분석 및 비즈니스 밸류업 리포트 자동화 플랫폼",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_initial_state(req: AnalysisRequest) -> dict:
    return {
        "query": req.query,
        "region_id": req.region_id,
        "requested_tools": [],
        "tool_results": {},
        "warnings": [],
    }


def _avg_confidence(tool_results: dict) -> float:
    scores = [r["confidence"] for r in tool_results.values() if r["status"] == "ok"]
    return round(sum(scores) / len(scores), 3) if scores else 0.0


@app.get("/health", response_model=HealthResponse, tags=["시스템"])
async def health():
    return HealthResponse(status="ok", version="0.1.0")


@app.post("/analyze", response_model=AnalysisResponse, tags=["분석"])
async def analyze(req: AnalysisRequest):
    """
    지역·질문을 입력받아 6개 AI 에이전트를 병렬 가동하고
    입지 분석 리포트를 반환합니다.
    """
    try:
        final_state = await graph.ainvoke(_build_initial_state(req))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    tool_results = {
        name: ToolResultResponse(
            tool=r["tool"],
            status=r["status"],
            confidence=r["confidence"],
            freshness_days=r.get("freshness_days"),
            summary=r.get("summary", ""),
            error=r.get("error"),
        )
        for name, r in final_state.get("tool_results", {}).items()
    }

    return AnalysisResponse(
        region_id=req.region_id,
        query=req.query,
        final_report=final_state.get("final_report", "리포트 생성 실패"),
        tool_results=tool_results,
        warnings=final_state.get("warnings", []),
        avg_confidence=_avg_confidence(final_state.get("tool_results", {})),
    )


@app.get("/analyze/stream", tags=["분석"])
async def analyze_stream_get(region_id: str, query: str):
    """GET 방식 SSE — 브라우저 EventSource 전용."""
    return await analyze_stream(AnalysisRequest(region_id=region_id, query=query))


@app.post("/analyze/stream", tags=["분석"])
async def analyze_stream(req: AnalysisRequest):
    """
    분석 결과를 Server-Sent Events(SSE) 스트림으로 반환합니다.
    각 에이전트 완료 시점에 중간 결과를 전송하고, 최종 리포트로 마무리합니다.
    """
    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            yield _sse("status", {"message": "에이전트 실행 시작", "region_id": req.region_id})

            async for event in graph.astream_events(
                _build_initial_state(req),
                version="v2",
            ):
                kind = event.get("event", "")
                name = event.get("name", "")

                # MCP 도구 완료 이벤트
                if kind == "on_chain_end" and name == "call_mcp_tool":
                    output = event.get("data", {}).get("output", {})
                    results = output.get("tool_results", {})
                    for tool_name, r in results.items():
                        yield _sse("tool_result", {
                            "tool": tool_name,
                            "status": r["status"],
                            "confidence": r["confidence"],
                            "summary": r.get("summary", ""),
                        })

                # 최종 리포트 완료
                elif kind == "on_chain_end" and name == "synthesize":
                    output = event.get("data", {}).get("output", {})
                    report = output.get("final_report", "")
                    if report:
                        yield _sse("report", {"final_report": report})

            yield _sse("done", {"message": "분석 완료"})

        except Exception as e:
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
