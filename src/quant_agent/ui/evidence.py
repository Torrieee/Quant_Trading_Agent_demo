"""Turn EngineResult trace into user-facing evidence / source cards."""

from __future__ import annotations

import json
from typing import Any

from ..engine import EngineResult

AGENT_LABELS = {
    "analysis_panel": "分析面板",
    "research": "量化研究",
    "risk": "风控",
    "reporter": "报告",
    "document_retrieval": "证据检索",
}

TOOL_LABELS = {
    "FundamentalAnalyst": "基本面分析师",
    "SentimentAnalyst": "情绪分析师",
    "ResearchAnalyst": "研究分析师",
    "aggregate_signals": "信号聚合投票",
    "get_market_data": "市场数据",
    "analyze_market_state": "市场状态识别",
    "get_strategy_recommendation": "策略推荐",
    "run_backtest": "策略回测",
    "search_evidence": "披露证据检索",
    "evidence_index": "证据索引",
    "episodic_memory": "历次分析记忆",
    "calculate_position_size": "仓位计算",
    "report": "分析报告",
}


def engine_result_to_dict(result: EngineResult) -> dict[str, Any]:
    return {
        "symbol": result.symbol,
        "success": result.success,
        "decision": result.decision,
        "individual_signals": result.individual_signals,
        "risk_verdict": result.risk_verdict,
        "risk_reason": result.risk_reason,
        "report": result.report,
        "final_state": _json_safe(result.final_state),
        "trace_steps": [_json_safe(s) for s in result.trace_steps],
        "agents_visited": result.agents_visited,
        "error": result.error,
    }


def build_evidence_view(result: EngineResult) -> dict[str, Any]:
    """Build structured evidence for UI: timeline + conclusion bindings."""
    timeline = []
    for idx, step in enumerate(result.trace_steps, start=1):
        agent = step.get("agent") or "unknown"
        tool = step.get("tool_name") or agent
        timeline.append(
            {
                "step_id": idx,
                "agent": agent,
                "agent_label": AGENT_LABELS.get(agent, agent),
                "tool_name": tool,
                "tool_label": TOOL_LABELS.get(str(tool), str(tool)),
                "rationale": step.get("rationale"),
                "arguments": step.get("arguments") or {},
                "observation": _json_safe(step.get("observation") or {}),
                "status": step.get("status", "ok"),
                "latency_ms": step.get("latency_ms", 0),
            }
        )

    bindings = _build_conclusion_bindings(result, timeline)
    return {
        "timeline": timeline,
        "conclusion_bindings": bindings,
        "agents_visited": result.agents_visited,
    }


def _build_conclusion_bindings(
    result: EngineResult,
    timeline: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    decision = result.decision or {}

    if decision:
        source_steps = [
            s["step_id"]
            for s in timeline
            if s["tool_name"] in ("aggregate_signals", "FundamentalAnalyst", "SentimentAnalyst", "ResearchAnalyst")
        ]
        bindings.append(
            {
                "conclusion_key": "初步投资决策",
                "value": f"{decision.get('signal_type', 'N/A').upper()} "
                f"(置信度 {decision.get('confidence', 0)}%)",
                "source_step_ids": source_steps or None,
                "description": "来自分析面板多 Agent 加权投票",
            }
        )

    if result.final_state.get("recommended_strategy"):
        ids = [s["step_id"] for s in timeline if s["tool_name"] in ("ResearchAnalyst", "get_strategy_recommendation")]
        bindings.append(
            {
                "conclusion_key": "推荐策略",
                "value": result.final_state["recommended_strategy"],
                "source_step_ids": ids or None,
                "description": "研究分析师 + Research 工具链",
            }
        )

    if result.final_state.get("position_size") is not None:
        ids = [s["step_id"] for s in timeline if s["tool_name"] == "calculate_position_size"]
        bindings.append(
            {
                "conclusion_key": "建议仓位",
                "value": result.final_state["position_size"],
                "source_step_ids": ids or None,
                "description": "Risk 智能体调用仓位计算工具",
            }
        )

    if result.risk_verdict:
        ids = [s["step_id"] for s in timeline if s["agent"] == "risk"]
        bindings.append(
            {
                "conclusion_key": "风控结论",
                "value": f"{result.risk_verdict}" + (f" — {result.risk_reason}" if result.risk_reason else ""),
                "source_step_ids": ids or None,
                "description": "风控规则校验 + Risk Agent 工具输出",
            }
        )

    if result.report:
        ids = [s["step_id"] for s in timeline if s["agent"] == "reporter" or s["tool_name"] == "report"]
        bindings.append(
            {
                "conclusion_key": "综合报告",
                "value": "见下方完整报告",
                "source_step_ids": ids or None,
                "description": "Reporter 基于 quant_state 中工具 observation 生成",
            }
        )

    for key in ("market_regime", "sharpe", "total_return"):
        if key in result.final_state:
            ids = [
                s["step_id"]
                for s in timeline
                if key in json.dumps(s.get("observation") or {}, default=str)
            ]
            bindings.append(
                {
                    "conclusion_key": key,
                    "value": result.final_state[key],
                    "source_step_ids": ids or None,
                    "description": f"final_state.{key}",
                }
            )

    if result.final_state.get("episodic_memory"):
        ids = [s["step_id"] for s in timeline if s["tool_name"] == "evidence_index"]
        mem = result.final_state["episodic_memory"]
        bindings.append(
            {
                "conclusion_key": "历次分析记忆",
                "value": f"{len(mem)} 条历史分析片段",
                "source_step_ids": ids or None,
                "description": "Episodic Memory：跨次 analyze 持久化的结构化会话记忆",
            }
        )

    return bindings


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, float):
        return round(obj, 6)
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)
