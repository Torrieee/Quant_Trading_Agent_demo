"""Tests for UI evidence formatting."""

from __future__ import annotations

from quant_agent.engine import EngineResult
from quant_agent.ui.evidence import build_evidence_view


def test_build_evidence_view_links_decision_to_trace():
    result = EngineResult(
        symbol="TEST",
        success=True,
        decision={"signal_type": "buy", "confidence": 72, "reasoning": "vote"},
        individual_signals={
            "FundamentalAnalyst": {"signal_type": "buy", "confidence": 70},
        },
        risk_verdict="approve",
        risk_reason="ok",
        report="# Report",
        final_state={
            "position_size": 0.12,
            "recommended_strategy": "mean_reversion",
            "preliminary_decision": {"signal_type": "buy", "confidence": 72},
        },
        trace_steps=[
            {
                "agent": "analysis_panel",
                "tool_name": "FundamentalAnalyst",
                "observation": {"signal_type": "buy", "confidence": 70},
                "status": "ok",
                "rationale": "fundamental done",
            },
            {
                "agent": "analysis_panel",
                "tool_name": "aggregate_signals",
                "observation": {"preliminary_decision": {"signal_type": "buy"}},
                "status": "ok",
            },
            {
                "agent": "risk",
                "tool_name": "calculate_position_size",
                "observation": {"position_size": 0.12},
                "status": "ok",
            },
            {
                "agent": "reporter",
                "tool_name": "report",
                "observation": {"report": "# Report"},
                "status": "ok",
            },
        ],
        agents_visited=["supervisor", "analysis_panel", "research", "risk", "reporter"],
    )

    view = build_evidence_view(result)
    assert len(view["timeline"]) == 4
    assert view["timeline"][0]["tool_label"] == "基本面分析师"
    bindings = {b["conclusion_key"]: b for b in view["conclusion_bindings"]}
    assert "初步投资决策" in bindings
    assert bindings["建议仓位"]["source_step_ids"] == [3]
    assert bindings["综合报告"]["source_step_ids"] == [4]
