import asyncio
import os
import time
from abc import ABC, abstractmethod

import httpx

from agents.state import ToolResult, ToolName


DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "8"))


class BaseMCPTool(ABC):
    tool_name: ToolName
    authority_score: float = 0.8
    max_valid_days: int = 365

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)

    async def call(self, region_id: str, query: str) -> ToolResult:
        try:
            result = await asyncio.wait_for(
                self._fetch(region_id, query),
                timeout=DEFAULT_TIMEOUT,
            )
            return result
        except asyncio.TimeoutError:
            return ToolResult(
                tool=self.tool_name,
                status="timeout",
                confidence=0.0,
                freshness_days=None,
                data_ref=None,
                summary="",
                error=f"{self.tool_name} 응답 시간 초과 ({DEFAULT_TIMEOUT}초)",
            )
        except Exception as e:
            return ToolResult(
                tool=self.tool_name,
                status="error",
                confidence=0.0,
                freshness_days=None,
                data_ref=None,
                summary="",
                error=str(e),
            )

    @abstractmethod
    async def _fetch(self, region_id: str, query: str) -> ToolResult:
        ...

    async def close(self):
        await self.client.aclose()
