"""Reporter 智能体：DeepSeek 生成 grounded 报告。"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from ..model_router import get_model_for_role
from ..state import WorkflowState
from ...compliance.guardrails import sanitize_report_text


def make_reporter_node(model: Any | None = None):
    def reporter_node(state: WorkflowState) -> WorkflowState:
        visited = list(state.get("agents_visited") or [])
        if "reporter" not in visited:
            visited.append("reporter")

        trace_steps = list(state.get("trace_steps") or [])
        quant_state = dict(state.get("quant_state") or {})
        step_count = state.get("step_count", 0) + 1

        llm = get_model_for_role("reporter", fallback=model)
        report = sanitize_report_text(_generate_report(llm, state, quant_state))

        trace_steps.append(
            {
                "agent": "reporter",
                "tool_name": "report",
                "arguments": {},
                "observation": {"report_preview": report[:200]},
                "latency_ms": 0.0,
                "status": "ok",
                "rationale": "Reporter 生成综合报告",
            }
        )

        return WorkflowState(
            report=report,
            trace_steps=trace_steps,
            agents_visited=visited,
            step_count=step_count,
            done=True,
        )

    return reporter_node


def _generate_report(llm: Any, state: WorkflowState, quant_state: dict[str, Any]) -> str:
    prompt = (
        f"任务: {state.get('task')}\n\n"
        f"量化状态（仅引用以下数值，勿编造）:\n{quant_state}\n\n"
        f"Risk 结论: {state.get('risk_verdict')}\n"
        f"初步决策: {state.get('preliminary_decision')}\n"
        "请输出 Markdown，包含：摘要、证据、风控、建议。"
    )
    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "你是 Reporter 智能体。只引用 quant_state 中已有数据"
                    "（含 evidence_snapshot、episodic_memory、semantic_memory、retrieved_documents 的 source_url），"
                    "缺失项请说明不可用。若 episodic_memory 存在，说明与上次分析的差异。"
                )
            ),
            HumanMessage(content=prompt),
        ]
    )
    content = response.content
    return content if isinstance(content, str) else str(content)
