"""协调器与各智能体节点共享的运行时状态。"""

from __future__ import annotations

from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    case_id: str
    symbol: str
    task: str
    quant_state: dict[str, Any]
    analysis_data: dict[str, Any]
    workflow_flags: dict[str, bool]
    analysis_complete: bool
    individual_signals: dict[str, Any]
    preliminary_decision: dict[str, Any] | None
    research_complete: bool
    reflection_complete: bool
    # 动态 Research 子图
    research_plan: list[dict[str, Any]]
    research_findings: list[dict[str, Any]]
    research_verification: dict[str, Any] | None
    replan_count: int
    max_replan: int
    risk_verdict: str | None
    risk_reason: str | None
    report: str | None
    retrieval_complete: bool
    human_approval: str | None
    compliance_warnings: list[str]
    trace_steps: list[dict[str, Any]]
    agents_visited: list[str]
    step_count: int
    max_steps: int
    max_research_steps: int
    max_risk_steps: int
    failures: list[str]
    gate: dict[str, Any]
    next_agent: str | None
    done: bool


RESEARCH_TOOL_NAMES = frozenset(
    {
        "get_market_data",
        "analyze_market_state",
        "get_strategy_recommendation",
        "run_backtest",
        "search_evidence",
    }
)

RISK_TOOL_NAMES = frozenset({"calculate_position_size"})

DEFAULT_AGENT_WEIGHTS: dict[str, float] = {
    "FundamentalAnalyst": 0.35,
    "SentimentAnalyst": 0.30,
    "ResearchAnalyst": 0.35,
}


def initial_state(
    *,
    case_id: str,
    symbol: str = "UNKNOWN",
    task: str,
    gate: dict[str, Any] | None = None,
    analysis_data: dict[str, Any] | None = None,
    workflow_flags: dict[str, bool] | None = None,
) -> WorkflowState:
    gate = gate or {}
    flags = workflow_flags or {
        "include_fundamental": True,
        "include_sentiment": True,
        "include_research_analyst": True,
    }
    return WorkflowState(
        case_id=case_id,
        symbol=symbol,
        task=task,
        quant_state={},
        analysis_data=analysis_data or {},
        workflow_flags=flags,
        analysis_complete=False,
        individual_signals={},
        preliminary_decision=None,
        retrieval_complete=False,
        reflection_complete=False,
        research_complete=False,
        research_plan=[],
        research_findings=[],
        research_verification=None,
        replan_count=0,
        max_replan=gate.get("max_replan", 1),
        risk_verdict=None,
        risk_reason=None,
        report=None,
        human_approval=None,
        compliance_warnings=[],
        trace_steps=[],
        agents_visited=[],
        step_count=0,
        max_steps=gate.get("max_steps", 12),
        max_research_steps=gate.get("max_research_steps", 6),
        max_risk_steps=gate.get("max_risk_steps", 3),
        failures=[],
        gate=gate,
        next_agent=None,
        done=False,
    )
