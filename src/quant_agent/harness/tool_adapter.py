"""Adapter wrapping TradingFunctionCaller with unified ToolCallResponse + latency."""

from __future__ import annotations

import time
from typing import Any

from ..llm_agent import TradingFunctionCaller
from .trace import ToolCallRequest, ToolCallResponse


class HarnessToolAdapter:
    def __init__(self, caller: TradingFunctionCaller | None = None) -> None:
        self._caller = caller or TradingFunctionCaller()

    @property
    def caller(self) -> TradingFunctionCaller:
        return self._caller

    def invoke(self, request: ToolCallRequest) -> ToolCallResponse:
        start = time.perf_counter()
        try:
            raw = self._caller.call_function(request.name, request.arguments)
            latency_ms = (time.perf_counter() - start) * 1000.0
            if isinstance(raw, dict) and "error" in raw:
                return ToolCallResponse(
                    ok=False,
                    data=raw,
                    error=str(raw["error"]),
                    latency_ms=latency_ms,
                )
            data = raw if isinstance(raw, dict) else {"result": raw}
            return ToolCallResponse(ok=True, data=data, error=None, latency_ms=latency_ms)
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000.0
            return ToolCallResponse(
                ok=False,
                data={"error": str(exc)},
                error=str(exc),
                latency_ms=latency_ms,
            )

    def invoke_named(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> ToolCallResponse:
        return self.invoke(ToolCallRequest(name=tool_name, arguments=arguments))
