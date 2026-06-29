"""Research 子图专用状态（支持 LangGraph Send 并行 Worker + reducer）。"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


def merge_quant_dict(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    """并行 Worker 合并 quant_state（后写覆盖同 key）。"""
    out = dict(left or {})
    if right:
        out.update(right)
    return out


def merge_findings(
    left: list[dict[str, Any]] | None,
    right: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """按 worker + task_id 去重，避免 retry / 并行重复 append。"""
    by_key: dict[str, dict[str, Any]] = {}
    for item in (left or []) + (right or []):
        key = str(item.get("task_id") or item.get("worker") or id(item))
        by_key[key] = item
    return list(by_key.values())


class ResearchSubgraphState(TypedDict, total=False):
    symbol: str
    task: str
    gate: dict[str, Any]
    quant_state: Annotated[dict[str, Any], merge_quant_dict]
    research_plan: list[dict[str, Any]]
    replan_count: int
    max_replan: int
    research_findings: Annotated[list[dict[str, Any]], merge_findings]
    trace_steps: Annotated[list[dict[str, Any]], operator.add]
    failures: Annotated[list[str], operator.add]
    step_count: Annotated[int, operator.add]
    research_verification: dict[str, Any] | None
    research_complete: bool
    # Send 传入的单 Worker 任务
    worker_task: dict[str, Any]
