"""Agent trace schema: rationale / tool_call / observation per step."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


def new_trace_id() -> str:
    return str(uuid.uuid4())


@dataclass
class ToolCallRequest:
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolCallResponse:
    ok: bool
    data: dict[str, Any]
    error: str | None
    latency_ms: float


@dataclass
class AgentTraceRecord:
    step_id: int
    rationale: str | None
    tool_name: str
    arguments: dict[str, Any]
    observation: dict[str, Any] | str
    status: str
    latency_ms: float
    token_usage: dict[str, int] | None = None
    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentTrace:
    trace_id: str
    case_id: str
    parent_trace_id: str | None
    attempt: int
    reflection_triggered: bool
    reflection_reason: str | None
    steps: list[AgentTraceRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "case_id": self.case_id,
            "parent_trace_id": self.parent_trace_id,
            "attempt": self.attempt,
            "reflection_triggered": self.reflection_triggered,
            "reflection_reason": self.reflection_reason,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def new_root(cls, case_id: str) -> AgentTrace:
        return cls(
            trace_id=new_trace_id(),
            case_id=case_id,
            parent_trace_id=None,
            attempt=1,
            reflection_triggered=False,
            reflection_reason=None,
        )
