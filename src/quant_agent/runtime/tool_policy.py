"""工具执行策略：超时、重试、输出截断、故障注入。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ToolResultStatus = Literal[
    "success",
    "retryable_error",
    "fatal_error",
    "approval_required",
]

RETRYABLE_ERRORS = frozenset(
    {
        "tool_timeout",
        "rate_limit",
        "transient_error",
        "empty_result",
    }
)


@dataclass
class ToolExecutionPolicy:
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retryable_errors: frozenset[str] = field(default_factory=lambda: RETRYABLE_ERRORS)
    max_output_chars: int = 8000
    # 故障注入（评测用）：{type, tool_name, fail_count, error_code}
    fault_injection: dict[str, Any] | None = None


@dataclass
class ToolResult:
    status: ToolResultStatus
    data: dict[str, Any] | None
    error_code: str | None
    latency_ms: float
    retry_count: int = 0
    output_truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.status == "success"
