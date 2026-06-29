"""Adapter wrapping TradingFunctionCaller with unified ToolCallResponse + latency."""

from __future__ import annotations

import json
import time
from typing import Any

from ..llm_agent import TradingFunctionCaller
from .tool_policy import ToolExecutionPolicy, ToolResult
from .trace import ToolCallRequest, ToolCallResponse


class HarnessToolAdapter:
    def __init__(
        self,
        caller: TradingFunctionCaller | None = None,
        *,
        policy: ToolExecutionPolicy | None = None,
    ) -> None:
        self._caller = caller or TradingFunctionCaller()
        self.policy = policy or ToolExecutionPolicy()
        self._fault_counts: dict[str, int] = {}

    @property
    def caller(self) -> TradingFunctionCaller:
        return self._caller

    def set_fault_injection(self, config: dict[str, Any] | None) -> None:
        """评测用：设置工具故障注入配置。"""
        self.policy.fault_injection = config
        self._fault_counts.clear()

    def invoke_with_policy(self, request: ToolCallRequest) -> ToolResult:
        """带重试、超时、截断与故障注入的执行。"""
        policy = self.policy
        last_error: str | None = None
        retry_count = 0

        for attempt in range(policy.max_retries + 1):
            injected = self._maybe_inject_fault(request.name)
            if injected is not None:
                last_error = injected
                if injected in policy.retryable_errors and attempt < policy.max_retries:
                    retry_count += 1
                    continue
                return ToolResult(
                    status="retryable_error" if injected in policy.retryable_errors else "fatal_error",
                    data={"error": injected},
                    error_code=injected,
                    latency_ms=0.0,
                    retry_count=retry_count,
                )

            start = time.perf_counter()
            try:
                raw = self._caller.call_function(request.name, request.arguments)
                latency_ms = (time.perf_counter() - start) * 1000.0
                if latency_ms > policy.timeout_seconds * 1000:
                    last_error = "tool_timeout"
                    if attempt < policy.max_retries:
                        retry_count += 1
                        continue
                    return ToolResult(
                        status="retryable_error",
                        data={"error": "tool_timeout"},
                        error_code="tool_timeout",
                        latency_ms=latency_ms,
                        retry_count=retry_count,
                    )

                if isinstance(raw, dict) and "error" in raw:
                    err = str(raw["error"])
                    last_error = err
                    if err in policy.retryable_errors and attempt < policy.max_retries:
                        retry_count += 1
                        continue
                    return ToolResult(
                        status="retryable_error" if err in policy.retryable_errors else "fatal_error",
                        data=raw,
                        error_code=err,
                        latency_ms=latency_ms,
                        retry_count=retry_count,
                    )

                data = raw if isinstance(raw, dict) else {"result": raw}
                truncated = False
                serialized = json.dumps(data, ensure_ascii=False, default=str)
                if len(serialized) > policy.max_output_chars:
                    truncated = True
                    data = {
                        "truncated": True,
                        "preview": serialized[: policy.max_output_chars],
                    }

                return ToolResult(
                    status="success",
                    data=data,
                    error_code=None,
                    latency_ms=latency_ms,
                    retry_count=retry_count,
                    output_truncated=truncated,
                )
            except Exception as exc:
                latency_ms = (time.perf_counter() - start) * 1000.0
                last_error = str(exc)
                code = "transient_error"
                if attempt < policy.max_retries:
                    retry_count += 1
                    continue
                return ToolResult(
                    status="retryable_error",
                    data={"error": last_error},
                    error_code=code,
                    latency_ms=latency_ms,
                    retry_count=retry_count,
                )

        return ToolResult(
            status="fatal_error",
            data={"error": last_error or "unknown"},
            error_code=last_error,
            latency_ms=0.0,
            retry_count=retry_count,
        )

    def _maybe_inject_fault(self, tool_name: str) -> str | None:
        fc = self.policy.fault_injection
        if not fc:
            return None
        if fc.get("type") != "tool_timeout":
            return None
        target = fc.get("tool_name")
        if target and target != tool_name:
            return None
        fail_count = int(fc.get("fail_count", 1))
        self._fault_counts[tool_name] = self._fault_counts.get(tool_name, 0) + 1
        if self._fault_counts[tool_name] <= fail_count:
            return str(fc.get("error_code", "tool_timeout"))
        return None

    def invoke(self, request: ToolCallRequest) -> ToolCallResponse:
        result = self.invoke_with_policy(request)
        return ToolCallResponse(
            ok=result.ok,
            data=result.data,
            error=result.error_code,
            latency_ms=result.latency_ms,
        )

    def invoke_named(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> ToolCallResponse:
        return self.invoke(ToolCallRequest(name=tool_name, arguments=arguments))
