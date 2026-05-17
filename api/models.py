from typing import Literal, Optional
from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    region_id: str = Field(
        ...,
        description="분석 대상 지역 — 행정동명, 주소, 또는 '위도,경도' 형식",
        examples=["서울특별시 강남구 역삼동", "37.4985,127.0278"],
    )
    query: str = Field(
        ...,
        description="분석 질문",
        examples=["이 지역 소규모 식당 인수 적합성 분석"],
    )


class ToolResultResponse(BaseModel):
    tool: str
    status: Literal["ok", "timeout", "error", "skipped"]
    confidence: float
    freshness_days: Optional[int]
    summary: str
    error: Optional[str] = None


class AnalysisResponse(BaseModel):
    region_id: str
    query: str
    final_report: str
    tool_results: dict[str, ToolResultResponse]
    warnings: list[str]
    avg_confidence: float


class HealthResponse(BaseModel):
    status: str
    version: str
