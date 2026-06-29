"""Research 智能体：ReAct 或动态子图（由 workflow_flags 控制）。"""

from __future__ import annotations

from typing import Any

from ..model_router import get_model_for_role
from ..react_loop import build_agent_messages, run_tool_react_loop
from ..state import RESEARCH_TOOL_NAMES, WorkflowState
from ..subgraphs import run_dynamic_research
from ..tools import get_openai_tool_specs_for_role


def make_research_node(adapter: Any, model: Any | None = None):
    def research_node(state: WorkflowState) -> WorkflowState:
        if state.get("step_count", 0) >= state.get("max_steps", 12):
            failures = list(state.get("failures") or [])
            failures.append("研究阶段超出 max_steps")
            return WorkflowState(
                research_complete=True,
                failures=failures,
                done=True,
            )

        flags = state.get("workflow_flags") or {}
        if flags.get("enable_dynamic_research"):
            return run_dynamic_research(state, adapter)

        trace_steps = list(state.get("trace_steps") or [])
        quant_state = dict(state.get("quant_state") or {})
        visited = list(state.get("agents_visited") or [])
        if "research" not in visited:
            visited.append("research")

        def record(tool_name: str, arguments: dict, observation: dict, latency_ms: float, status: str):
            trace_steps.append(
                {
                    "agent": "research",
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "observation": observation,
                    "latency_ms": latency_ms,
                    "status": status,
                    "rationale": f"Research 智能体调用 {tool_name}",
                }
            )

        llm = get_model_for_role("research", fallback=model)
        tool_specs = get_openai_tool_specs_for_role(adapter, "research")
        messages = build_agent_messages(
            system=(
                "你是量化研究智能体。context 中可能含 evidence_snapshot、episodic_memory（历次分析）"
                "与 preliminary_decision。优先引用已有证据与历史分析；不足时可调用 search_evidence。"
                "若已有所需 market_regime，可跳过 analyze_market_state，"
                "调用 get_strategy_recommendation 时请传入 symbol 与 risk_flags（若有）。"
                "不要计算仓位（Risk 智能体负责）。信息充分后停止调用工具。"
            ),
            task=state.get("task") or "完成量化研究。",
            context=quant_state,
            symbol=state.get("symbol"),
        )
        step_count = state.get("step_count", 0)
        failures = list(state.get("failures") or [])
        step_count, quant_state, react_failures = run_tool_react_loop(
            adapter=adapter,
            model=llm,
            tool_specs=tool_specs,
            allowed_tools=set(RESEARCH_TOOL_NAMES),
            messages=messages,
            quant_state=quant_state,
            max_loops=state.get("max_research_steps", 6),
            max_total_steps=state.get("max_steps", 12),
            step_count=step_count,
            record=record,
            symbol=state.get("symbol"),
        )
        failures.extend(react_failures)

        return WorkflowState(
            quant_state=quant_state,
            trace_steps=trace_steps,
            agents_visited=visited,
            step_count=step_count,
            research_complete=True,
            failures=failures,
        )

    return research_node
