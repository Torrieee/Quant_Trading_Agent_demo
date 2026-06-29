"""Research 动态子图：任务规划。"""

from __future__ import annotations

from typing import Any


def build_research_plan(state: dict[str, Any]) -> list[dict[str, Any]]:
    """规则 Planner：根据 task 与 quant_state 生成 worker 任务列表。"""
    task = (state.get("task") or "").lower()
    quant = dict(state.get("quant_state") or {})
    risk_flags = list(quant.get("risk_flags") or [])
    plan: list[dict[str, Any]] = []

    need_evidence = any(
        kw in task
        for kw in (
            "risk",
            "supply",
            "供应链",
            "监管",
            "regulatory",
            "going concern",
            "披露",
        )
    ) or bool(risk_flags)

    if need_evidence or state.get("replan_count", 0) > 0:
        query = task[:200] if task else "risk factors supply chain"
        plan.append(
            {
                "task_id": "evidence:search_evidence",
                "worker": "evidence",
                "goal": "检索与任务相关的披露与风险证据",
                "tool": "search_evidence",
                "tool_args": {"query": query},
                "required_evidence": True,
            }
        )

    if not quant.get("market_regime"):
        plan.append(
            {
                "task_id": "market:analyze_market_state",
                "worker": "market",
                "goal": "判断当前市场状态",
                "tool": "analyze_market_state",
                "tool_args": {},
                "required_evidence": False,
            }
        )

    plan.append(
        {
            "task_id": "strategy:get_strategy_recommendation",
            "worker": "strategy",
            "goal": "推荐交易策略",
            "tool": "get_strategy_recommendation",
            "tool_args": {"market_state": quant.get("market_regime") or "ranging"},
            "required_evidence": False,
        }
    )

    return plan
