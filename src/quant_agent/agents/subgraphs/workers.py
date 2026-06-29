"""Research 动态子图：单 Worker 任务执行（供 Send 并行调度）。"""

from __future__ import annotations

import time
from typing import Any

from ...runtime.tool_adapter import HarnessToolAdapter
from ...runtime.trace import ToolCallRequest
from ..tools import enrich_tool_arguments, merge_observation


def execute_worker_task(
    state: dict[str, Any],
    adapter: HarnessToolAdapter,
) -> dict[str, Any]:
    """
    执行单个 worker_task，返回子图 state 增量（供 reducer 合并）。
    """
    task = dict(state.get("worker_task") or {})
    if not task:
        return {"failures": ["worker: 缺少 worker_task"]}

    quant = dict(state.get("quant_state") or {})
    symbol = state.get("symbol")
    worker = task.get("worker", "unknown")
    tool_name = task.get("tool", "")
    task_id = task.get("task_id") or f"{worker}:{tool_name}"
    raw_args = dict(task.get("tool_args") or {})
    args = enrich_tool_arguments(tool_name, raw_args, quant, symbol=symbol)

    start = time.perf_counter()
    result = adapter.invoke_with_policy(ToolCallRequest(name=tool_name, arguments=args))
    latency_ms = result.latency_ms or (time.perf_counter() - start) * 1000.0
    data = result.data if isinstance(result.data, dict) else {"result": result.data}
    if result.retry_count:
        data = {**data, "retry_count": result.retry_count}

    status = "ok" if result.ok else "failed"
    trace_step = {
        "agent": f"research_{worker}",
        "tool_name": tool_name,
        "arguments": args,
        "observation": data,
        "latency_ms": latency_ms,
        "status": status,
        "rationale": task.get("goal", f"{worker} worker"),
        "parallel": True,
        "task_id": task_id,
    }

    if result.ok:
        merge_observation(quant, data)

    evidence_ids: list[str] = []
    if tool_name == "search_evidence":
        docs = data.get("retrieved_documents") or data.get("documents") or []
        if isinstance(docs, list):
            evidence_ids = [
                str(d.get("doc_id"))
                for d in docs
                if isinstance(d, dict) and d.get("doc_id")
            ]
    elif quant.get("evidence_snapshot"):
        evidence_ids = [
            str(d.get("doc_id"))
            for d in quant.get("evidence_snapshot", [])
            if isinstance(d, dict) and d.get("doc_id")
        ][:3]

    claim = _finding_claim(worker, tool_name, data, quant)
    finding = {
        "task_id": task_id,
        "worker": worker,
        "claim": claim,
        "confidence": 0.85 if result.ok else 0.2,
        "evidence_ids": evidence_ids,
        "tools_used": [tool_name],
        "status": "ok" if result.ok else "insufficient",
    }

    return {
        "quant_state": quant,
        "research_findings": [finding],
        "trace_steps": [trace_step],
        "step_count": 1,
    }


def run_research_workers(
    state: dict[str, Any],
    adapter: HarnessToolAdapter,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], int]:
    """顺序执行全部 plan（兼容旧路径 / 测试）。"""
    quant = dict(state.get("quant_state") or {})
    plan = list(state.get("research_plan") or [])
    findings: list[dict[str, Any]] = []
    trace_steps: list[dict[str, Any]] = []
    steps = 0

    for task in plan:
        partial = execute_worker_task(
            {**state, "quant_state": quant, "worker_task": task},
            adapter,
        )
        quant = partial.get("quant_state") or quant
        findings.extend(partial.get("research_findings") or [])
        trace_steps.extend(partial.get("trace_steps") or [])
        steps += int(partial.get("step_count") or 0)

    return quant, findings, trace_steps, steps


def _finding_claim(worker: str, tool: str, data: dict, quant: dict) -> str:
    if tool == "get_strategy_recommendation":
        strat = data.get("recommended_strategy") or quant.get("recommended_strategy")
        return f"推荐策略: {strat or 'unknown'}"
    if tool == "analyze_market_state":
        regime = data.get("market_regime") or quant.get("market_regime")
        return f"市场状态: {regime or 'unknown'}"
    if tool == "search_evidence":
        n = len(data.get("retrieved_documents") or data.get("documents") or [])
        return f"检索到 {n} 条证据"
    return f"{worker} 完成 {tool}"
