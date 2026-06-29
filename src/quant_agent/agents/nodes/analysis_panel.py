"""分析面板节点：顺序运行基本面、情绪与量化研究规则智能体并加权投票。"""

from __future__ import annotations

from typing import Any

from ..serialization import resolve_analysis_data
from ..fundamental import FundamentalAgent
from ..research_analyst import ResearchAnalystAgent
from ..sentiment import SentimentAgent
from ..signal_aggregate import aggregate_signals
from ..state import WorkflowState


def analysis_panel_node(state: WorkflowState) -> WorkflowState:
    """执行离线规则分析并写入初步决策与 trace。"""
    visited = list(state.get("agents_visited") or [])
    if "analysis_panel" not in visited:
        visited.append("analysis_panel")

    flags = state.get("workflow_flags") or {}
    symbol = state.get("symbol") or "UNKNOWN"
    data = resolve_analysis_data(state)
    trace_steps = list(state.get("trace_steps") or [])
    quant_state = dict(state.get("quant_state") or {})

    signals: dict[str, Any] = {}

    if flags.get("include_fundamental", True):
        sig = FundamentalAgent().analyze(symbol, data)
        signals[sig.agent_name] = sig
        _append_signal_trace(trace_steps, sig)

    if flags.get("include_sentiment", True):
        sig = SentimentAgent().analyze(symbol, data)
        signals[sig.agent_name] = sig
        _append_signal_trace(trace_steps, sig)

    if flags.get("include_research_analyst", True):
        sig = ResearchAnalystAgent().analyze(symbol, data)
        signals[sig.agent_name] = sig
        _append_signal_trace(trace_steps, sig)
        # 将推荐策略写入 quant_state，供后续研究与报告引用
        strategy = sig.metadata.get("recommended_strategy")
        if strategy:
            quant_state["recommended_strategy"] = strategy
        regime = sig.metadata.get("market_regime")
        if regime:
            quant_state["market_regime"] = regime

    preliminary = aggregate_signals(signals)
    serialized = {name: s.model_dump() for name, s in signals.items()}
    quant_state["individual_signals"] = serialized
    quant_state["preliminary_decision"] = preliminary

    trace_steps.append(
        {
            "agent": "analysis_panel",
            "tool_name": "aggregate_signals",
            "arguments": {"symbol": symbol},
            "observation": {"preliminary_decision": preliminary},
            "latency_ms": 0.0,
            "status": "ok",
            "rationale": "分析面板完成加权投票",
        }
    )

    return WorkflowState(
        quant_state=quant_state,
        individual_signals=serialized,
        preliminary_decision=preliminary,
        analysis_complete=True,
        trace_steps=trace_steps,
        agents_visited=visited,
        step_count=state.get("step_count", 0) + len(signals) + 1,
    )


def _append_signal_trace(trace_steps: list[dict], signal: Any) -> None:
    trace_steps.append(
        {
            "agent": "analysis_panel",
            "tool_name": signal.agent_name,
            "arguments": {},
            "observation": signal.model_dump(),
            "latency_ms": 0.0,
            "status": "ok",
            "rationale": f"{signal.agent_name} 完成分析",
        }
    )
