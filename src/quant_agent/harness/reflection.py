"""Deterministic and optional LLM reflection retry."""

from __future__ import annotations

import json
from typing import Any, Callable

from ..llm_agent import TradingFunctionCaller
from .llm_client import DEFAULT_LIVE_MODEL, chat_json_completion


def classify_failure_types(evaluations: dict[str, dict[str, Any]]) -> list[str]:
    types: list[str] = []
    ev = evaluations.get("evidence_coverage", {})
    if not ev.get("passed", True):
        types.extend(ev.get("failure_types", ["missing_evidence"]))
    return types


def should_reflect(
    case: dict[str, Any],
    evaluations: dict[str, dict[str, Any]],
) -> tuple[bool, str | None]:
    reflection = case.get("reflection") or {}
    if not reflection.get("enabled"):
        return False, None
    on_failure = reflection.get("on_failure_retry") or {}
    for failure_type in classify_failure_types(evaluations):
        if failure_type in on_failure:
            return True, failure_type
    return False, None


def build_retry_plan(case: dict[str, Any], failure_type: str) -> list[dict[str, Any]]:
    reflection = case.get("reflection") or {}
    spec = (reflection.get("on_failure_retry") or {}).get(failure_type)
    if spec is None:
        return []
    if isinstance(spec, list):
        return list(spec)
    return [spec]


def build_llm_retry_plan(
    case: dict[str, Any],
    trace: dict[str, Any],
    evaluations: dict[str, dict[str, Any]],
    caller: TradingFunctionCaller,
    client: Any | None,
    *,
    model: str = DEFAULT_LIVE_MODEL,
    completion_fn: Callable[..., str] | None = None,
) -> list[dict[str, Any]]:
    """Ask LLM for one retry tool step; return [] on failure."""
    if client is None and completion_fn is None:
        return []
    try:
        tools = {f["name"] for f in caller.get_available_functions()}
        system = (
            "Given a failed agent trace, suggest ONE retry tool step as JSON: "
            '{"retry":[{"tool":"<name>","arguments":{...},"rationale":"..."}]} '
            f"Use only tools: {sorted(tools)}"
        )
        user = json.dumps(
            {
                "case_name": case.get("name"),
                "trace": trace,
                "evaluations": evaluations,
            },
            ensure_ascii=False,
            default=str,
        )
        if completion_fn is not None:
            raw = completion_fn(system=system, user=user)
        else:
            raw = chat_json_completion(
                client, model=model, system=system, user=user
            )
        payload = json.loads(raw)
        steps = payload.get("retry") or payload.get("plan") or []
        if not isinstance(steps, list) or not steps:
            return []
        step = steps[0]
        tool = step.get("tool") or step.get("tool_name")
        if not tool or tool not in tools:
            return []
        return [
            {
                "tool": tool,
                "arguments": dict(step.get("arguments") or {}),
                **({"rationale": step["rationale"]} if step.get("rationale") else {}),
            }
        ]
    except Exception:
        return []


def resolve_retry_plan(
    case: dict[str, Any],
    evaluations: dict[str, dict[str, Any]],
    *,
    live: bool,
    trace: dict[str, Any] | None = None,
    caller: TradingFunctionCaller | None = None,
    client: Any | None = None,
) -> tuple[list[dict[str, Any]], str | None, str]:
    """Return (plan, failure_reason, reflection_mode)."""
    reflect, reason = should_reflect(case, evaluations)
    if not reflect:
        return [], None, "none"

    deterministic = build_retry_plan(case, reason or "")
    if deterministic:
        return deterministic, reason, "deterministic"

    if live and case.get("live_reflection_enabled") and caller is not None:
        llm_plan = build_llm_retry_plan(
            case,
            trace or {},
            evaluations,
            caller,
            client,
        )
        if llm_plan:
            return llm_plan, reason or "llm_reflection", "llm"

    return [], reason, "none"
