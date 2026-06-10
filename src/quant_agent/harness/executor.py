"""Multi-step tool executor with cross-step state and max_steps limit."""

from __future__ import annotations

from typing import Any

from .tool_adapter import HarnessToolAdapter
from .trace import AgentTrace, AgentTraceRecord, ToolCallRequest


def resolve_step_arguments(step: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    arguments = dict(step.get("arguments") or {})
    for arg_name, state_key in (step.get("arguments_from_state") or {}).items():
        if state_key not in state:
            raise KeyError(
                f"arguments_from_state: key '{state_key}' not in state for arg '{arg_name}'"
            )
        arguments[arg_name] = state[state_key]
    return arguments


def merge_observation_into_state(state: dict[str, Any], observation: dict[str, Any]) -> None:
    for key, value in observation.items():
        state[key] = value


class Executor:
    def __init__(
        self,
        adapter: HarnessToolAdapter,
        *,
        max_steps: int = 6,
    ) -> None:
        self.adapter = adapter
        self.max_steps = max_steps

    def run_plan(
        self,
        plan: list[dict[str, Any]],
        trace: AgentTrace,
        *,
        initial_state: dict[str, Any] | None = None,
        rationale_prefix: str | None = None,
    ) -> tuple[dict[str, Any], list[str]]:
        state: dict[str, Any] = dict(initial_state or {})
        errors: list[str] = []

        if len(plan) > self.max_steps:
            errors.append(
                f"max_steps_exceeded: plan has {len(plan)} steps, limit is {self.max_steps}"
            )
            return state, errors

        for idx, step in enumerate(plan):
            step_id = idx + 1
            tool_name = step.get("tool") or step.get("tool_name")
            if not tool_name:
                errors.append(f"step_{step_id}: missing tool name")
                break

            rationale = step.get("rationale")
            if rationale is None and rationale_prefix:
                rationale = f"{rationale_prefix} step {step_id}: call {tool_name}"

            try:
                arguments = resolve_step_arguments(step, state)
            except KeyError as exc:
                record = AgentTraceRecord(
                    step_id=step_id,
                    rationale=rationale,
                    tool_name=tool_name,
                    arguments=dict(step.get("arguments") or {}),
                    observation={"error": str(exc)},
                    status="failed",
                    latency_ms=0.0,
                    error_type="arguments_from_state",
                    error_message=str(exc),
                )
                trace.steps.append(record)
                errors.append(str(exc))
                break

            response = self.adapter.invoke(
                ToolCallRequest(name=tool_name, arguments=arguments)
            )
            observation: dict[str, Any] | str = response.data
            if response.ok:
                merge_observation_into_state(state, response.data)
                status = "ok"
                error_type = None
                error_message = None
            else:
                status = "failed"
                error_type = "tool_error"
                error_message = response.error
                errors.append(
                    f"step_{step_id}: tool '{tool_name}' failed: {response.error}"
                )

            trace.steps.append(
                AgentTraceRecord(
                    step_id=step_id,
                    rationale=rationale,
                    tool_name=tool_name,
                    arguments=arguments,
                    observation=observation,
                    status=status,
                    latency_ms=response.latency_ms,
                    error_type=error_type,
                    error_message=error_message,
                )
            )

            if not response.ok:
                break

        return state, errors
