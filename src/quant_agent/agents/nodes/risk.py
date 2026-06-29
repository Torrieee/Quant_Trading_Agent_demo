"""Risk 智能体：DeepSeek ReAct 仓位计算 + 规则硬否决。"""

from __future__ import annotations

from typing import Any

from ..model_router import get_model_for_role
from ..react_loop import build_agent_messages, run_tool_react_loop
from ..state import RISK_TOOL_NAMES, WorkflowState
from ..tools import get_openai_tool_specs_for_role


def make_risk_node(adapter: Any, model: Any | None = None):
    def risk_node(state: WorkflowState) -> WorkflowState:
        trace_steps = list(state.get("trace_steps") or [])
        quant_state = dict(state.get("quant_state") or {})
        visited = list(state.get("agents_visited") or [])
        if "risk" not in visited:
            visited.append("risk")

        gate = state.get("gate") or {}
        failures = list(state.get("failures") or [])
        step_count = state.get("step_count", 0)

        def record(tool_name: str, arguments: dict, observation: dict, latency_ms: float, status: str):
            trace_steps.append(
                {
                    "agent": "risk",
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "observation": observation,
                    "latency_ms": latency_ms,
                    "status": status,
                    "rationale": f"Risk 智能体调用 {tool_name}",
                }
            )

        llm = get_model_for_role("risk", fallback=model)
        tool_specs = get_openai_tool_specs_for_role(adapter, "risk")
        messages = build_agent_messages(
            system=(
                "你是 Risk 智能体。仅可使用 calculate_position_size。"
                "根据上下文选择方法与参数，不确定时偏保守。"
            ),
            task=state.get("task") or "计算合适仓位。",
            context=quant_state,
            symbol=state.get("symbol"),
        )
        step_count, quant_state, react_failures = run_tool_react_loop(
            adapter=adapter,
            model=llm,
            tool_specs=tool_specs,
            allowed_tools=set(RISK_TOOL_NAMES),
            messages=messages,
            quant_state=quant_state,
            max_loops=state.get("max_risk_steps", 3),
            max_total_steps=state.get("max_steps", 12),
            step_count=step_count,
            record=record,
        )
        failures.extend(react_failures)

        verdict, reason = evaluate_risk_rules(quant_state, gate, failures)
        return WorkflowState(
            quant_state=quant_state,
            trace_steps=trace_steps,
            agents_visited=visited,
            step_count=step_count,
            risk_verdict=verdict,
            risk_reason=reason,
            failures=failures if verdict == "reject" else list(state.get("failures") or []),
            done=verdict == "reject",
        )

    return risk_node


def evaluate_risk_rules(
    quant_state: dict[str, Any],
    gate: dict[str, Any],
    failures: list[str],
) -> tuple[str, str | None]:
    """规则型硬否决：超出仓位上限等情况直接 reject。"""
    max_position = gate.get("max_position_size", 1.0)
    position = quant_state.get("position_size")
    if position is None:
        failures.append("risk: 缺少 position_size")
        return "reject", "missing position_size"

    try:
        pos_f = float(position)
    except (TypeError, ValueError):
        failures.append("risk: position_size 非数值")
        return "reject", "invalid position_size"

    if pos_f < 0:
        failures.append("risk: position_size 为负")
        return "reject", "negative position_size"

    if pos_f > max_position:
        failures.append(f"risk: position_size {pos_f} 超过上限 {max_position}")
        return "reject", f"position_size exceeds max {max_position}"

    min_position = gate.get("min_position_size")
    if min_position is not None and pos_f < float(min_position):
        failures.append(f"risk: position_size {pos_f} 低于下限 {min_position}")
        return "reject", f"position_size below min {min_position}"

    return "pass", None
