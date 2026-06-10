"""Planners for agent task cases (offline YAML + optional LLM)."""

from __future__ import annotations

import json
from typing import Any, Callable, Protocol

from ..llm_agent import TradingFunctionCaller
from .llm_client import DEFAULT_LIVE_MODEL, chat_json_completion


class Planner(Protocol):
    def build_plan(self, case: dict[str, Any]) -> list[dict[str, Any]]:
        ...


class OfflinePlanner:
    """Read explicit tool steps from YAML case `plan` field."""

    def build_plan(self, case: dict[str, Any]) -> list[dict[str, Any]]:
        plan = case.get("plan")
        if not plan:
            offline_plan = case.get("offline_plan")
            if offline_plan:
                plan = offline_plan
        if not plan:
            raise ValueError(
                f"Case '{case.get('name', '<unknown>')}' has no plan or offline_plan"
            )
        return list(plan)


def _validate_plan_steps(
    steps: list[dict[str, Any]], available_tools: set[str]
) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    for step in steps:
        tool = step.get("tool") or step.get("tool_name")
        if not tool or tool not in available_tools:
            raise ValueError(f"invalid_tool_in_plan: {tool}")
        validated.append(
            {
                "tool": tool,
                "arguments": dict(step.get("arguments") or {}),
                **({"rationale": step["rationale"]} if step.get("rationale") else {}),
            }
        )
    return validated


class LLMPlanner:
    """Generate tool plan via LLM; fallback to OfflinePlanner on failure."""

    def __init__(
        self,
        caller: TradingFunctionCaller,
        client: Any | None,
        *,
        model: str = DEFAULT_LIVE_MODEL,
        fallback: OfflinePlanner | None = None,
        completion_fn: Callable[..., str] | None = None,
    ) -> None:
        self.caller = caller
        self.client = client
        self.model = model
        self.fallback = fallback or OfflinePlanner()
        self._completion_fn = completion_fn

    def build_plan(self, case: dict[str, Any]) -> list[dict[str, Any]]:
        if self.client is None and self._completion_fn is None:
            return self.fallback.build_plan(case)
        try:
            tools = {f["name"] for f in self.caller.get_available_functions()}
            system = (
                "You plan multi-tool agent tasks. Return JSON: "
                '{"plan":[{"tool":"<name>","arguments":{...},"rationale":"..."}]} '
                f"Use only tools: {sorted(tools)}"
            )
            user = json.dumps(
                {
                    "case_name": case.get("name"),
                    "mode": case.get("mode"),
                    "gate": case.get("gate", {}),
                    "task_hint": case.get("task_hint", case.get("name")),
                },
                ensure_ascii=False,
            )
            if self._completion_fn is not None:
                raw = self._completion_fn(system=system, user=user)
            else:
                raw = chat_json_completion(
                    self.client, model=self.model, system=system, user=user
                )
            payload = json.loads(raw)
            steps = payload.get("plan") or payload.get("steps") or []
            if not isinstance(steps, list) or not steps:
                raise ValueError("empty_llm_plan")
            return _validate_plan_steps(steps, tools)
        except Exception:
            return self.fallback.build_plan(case)


def select_planner(
    case: dict[str, Any],
    *,
    live: bool,
    caller: TradingFunctionCaller,
    client: Any | None,
    offline: OfflinePlanner | None = None,
) -> Planner:
    offline = offline or OfflinePlanner()
    use_llm = live and (
        case.get("live_planner_enabled")
        or case.get("mode") == "live"
    )
    if use_llm:
        return LLMPlanner(caller, client, fallback=offline)
    return offline
