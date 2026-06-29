"""Research 后轻量反思节点（可选）。"""

from __future__ import annotations

from typing import Any

from ..state import WorkflowState


def reflection_node(state: WorkflowState) -> WorkflowState:
    """
    规则式反思：检查 quant_state 是否具备研究产出；
    若缺失策略推荐则写入 failures 提示（不阻断流程）。
    """
    flags = state.get("workflow_flags") or {}
    if not flags.get("enable_reflection", False):
        return WorkflowState()

    quant = dict(state.get("quant_state") or {})
    failures = list(state.get("failures") or [])
    trace_steps = list(state.get("trace_steps") or [])

    issues: list[str] = []
    if not quant.get("recommended_strategy"):
        issues.append("research 未写入 recommended_strategy")
    if not quant.get("evidence_snapshot"):
        issues.append("缺少 evidence_snapshot")

    if issues:
        failures.extend([f"reflection: {x}" for x in issues])

    trace_steps.append(
        {
            "agent": "reflection",
            "tool_name": "reflection_check",
            "arguments": {},
            "observation": {"issues": issues, "ok": not issues},
            "latency_ms": 0.0,
            "status": "ok" if not issues else "warn",
            "rationale": "规则反思检查研究产出完整性",
        }
    )

    visited = list(state.get("agents_visited") or [])
    if "reflection" not in visited:
        visited.append("reflection")

    return WorkflowState(
        quant_state=quant,
        trace_steps=trace_steps,
        failures=failures,
        agents_visited=visited,
        reflection_complete=True,
        step_count=state.get("step_count", 0) + 1,
    )
