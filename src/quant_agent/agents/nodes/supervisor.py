"""Supervisor 路由节点。

纯代码规则路由（非 LLM）：根据 WorkflowState 标志位选择下一业务节点。
所有允许的状态转移在 `_choose_next()` 中定义，属于固定拓扑、受约束路由。
"""

from __future__ import annotations

from typing import Literal

from ..state import WorkflowState


def supervisor_node(state: WorkflowState) -> WorkflowState:
    visited = list(state.get("agents_visited") or [])
    if "supervisor" not in visited:
        visited.append("supervisor")

    return WorkflowState(
        agents_visited=visited,
        next_agent=_choose_next(state),
    )


def _choose_next(state: WorkflowState) -> str | None:
    if state.get("done"):
        return None
    if state.get("human_approval") == "reject":
        return None
    if not state.get("analysis_complete"):
        return "analysis_panel"
    if not state.get("retrieval_complete"):
        return "document_retrieval"
    if not state.get("research_complete"):
        return "research"
    flags = state.get("workflow_flags") or {}
    if flags.get("enable_reflection") and not state.get("reflection_complete"):
        return "reflection"
    if state.get("risk_verdict") is None:
        return "risk"
    if state.get("risk_verdict") == "reject":
        return None
    if not state.get("report"):
        return "reporter"
    return None


def route_supervisor(
    state: WorkflowState,
) -> Literal[
    "analysis_panel",
    "document_retrieval",
    "research",
    "reflection",
    "risk",
    "reporter",
    "__end__",
]:
    nxt = state.get("next_agent")
    if nxt == "analysis_panel":
        return "analysis_panel"
    if nxt == "document_retrieval":
        return "document_retrieval"
    if nxt == "research":
        return "research"
    if nxt == "reflection":
        return "reflection"
    if nxt == "risk":
        return "risk"
    if nxt == "reporter":
        return "reporter"
    return "__end__"
