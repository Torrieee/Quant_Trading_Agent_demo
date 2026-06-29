"""Research / Risk 智能体共用的 ReAct 工具循环。"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import BaseMessage, ToolMessage

from ..runtime.tool_adapter import HarnessToolAdapter
from .tools import RecordFn, enrich_tool_arguments, execute_tool_step, merge_observation


def run_tool_react_loop(
    *,
    adapter: HarnessToolAdapter,
    model: Any,
    tool_specs: list[dict[str, Any]],
    allowed_tools: set[str],
    messages: list[BaseMessage],
    quant_state: dict[str, Any],
    max_loops: int,
    max_total_steps: int,
    step_count: int,
    record: RecordFn | None = None,
    symbol: str | None = None,
) -> tuple[int, dict[str, Any], list[str]]:
    failures: list[str] = []
    if not tool_specs:
        failures.append("react: 无可用工具")
        return step_count, quant_state, failures

    for _ in range(max_loops):
        response = model.bind_tools(tool_specs).invoke(messages)
        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            break

        messages.append(response)
        for call in tool_calls:
            tool_name = call["name"]
            raw_args = call.get("args") or call.get("arguments") or {}
            if isinstance(raw_args, str):
                arguments = json.loads(raw_args)
            else:
                arguments = dict(raw_args)

            arguments = enrich_tool_arguments(
                tool_name, arguments, quant_state, symbol=symbol
            )

            if tool_name not in allowed_tools:
                failures.append(f"react: 不允许的工具 {tool_name}")
                continue

            observation, ok, _latency_ms, err = execute_tool_step(
                adapter,
                tool_name,
                arguments,
                on_invoke=record,
            )
            if not ok:
                failures.append(f"react: 工具 '{tool_name}' 执行失败: {err}")
            merge_observation(quant_state, observation)
            step_count += 1
            messages.append(
                ToolMessage(
                    content=json.dumps(observation, ensure_ascii=False, default=str),
                    tool_call_id=call["id"],
                )
            )
            if step_count >= max_total_steps:
                failures.append("react 循环超出 max_steps")
                return step_count, quant_state, failures

    return step_count, quant_state, failures


def build_agent_messages(
    *,
    system: str,
    task: str,
    context: dict[str, Any] | None = None,
) -> list[BaseMessage]:
    from langchain_core.messages import HumanMessage, SystemMessage

    user = task
    if context:
        user = f"{task}\n\n上下文:\n{json.dumps(context, ensure_ascii=False, default=str)}"
    return [SystemMessage(content=system), HumanMessage(content=user)]
