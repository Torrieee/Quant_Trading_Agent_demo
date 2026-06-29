"""LangGraph 运行时单元测试（注入假模型，无需网络）。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_agent.agents.coordinator import run_workflow
from quant_agent.agents.nodes.risk import evaluate_risk_rules
from quant_agent.agents.nodes.supervisor import route_supervisor, supervisor_node
from quant_agent.agents.state import initial_state
from quant_agent.features import add_daily_returns
from quant_agent.eval.fake_model import RoleAwareFakeModel
from quant_agent.runtime.runner import RuntimeRunner

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_ohlcv.csv"


def _analysis_data() -> dict:
    df = pd.read_csv(FIXTURE, index_col=0, parse_dates=True)
    if "ret" not in df.columns:
        df = add_daily_returns(df)
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]
    return {
        "historical_data": df,
        "stock_info": {"symbol": "FIXTURE", "pe_ratio": 18, "pb_ratio": 2.5},
    }


def _merge(state: dict, update: dict) -> dict:
    merged = dict(state)
    merged.update(update)
    return merged


def test_supervisor_routing_sequence():
    state = initial_state(
        case_id="route",
        task="t",
        gate={},
        analysis_data=_analysis_data(),
    )
    state = _merge(state, supervisor_node(state))
    assert route_supervisor(state) == "analysis_panel"

    state = _merge(state, {"analysis_complete": True})
    state = _merge(state, supervisor_node(state))
    assert route_supervisor(state) == "document_retrieval"

    state = _merge(state, {"retrieval_complete": True})
    state = _merge(state, supervisor_node(state))
    assert route_supervisor(state) == "research"

    state = _merge(state, {"research_complete": True})
    state = _merge(state, supervisor_node(state))
    assert route_supervisor(state) == "risk"

    state = _merge(state, {"risk_verdict": "pass"})
    state = _merge(state, supervisor_node(state))
    assert route_supervisor(state) == "reporter"


def test_risk_rules_reject_oversized():
    failures: list[str] = []
    verdict, reason = evaluate_risk_rules(
        {"position_size": 0.5},
        {"max_position_size": 0.1},
        failures,
    )
    assert verdict == "reject"
    assert reason
    assert failures


def test_full_graph_with_fake_model():
    state = initial_state(
        case_id="mock_graph",
        task="Recommend strategy for ranging market",
        gate={"max_steps": 12},
        analysis_data=_analysis_data(),
    )
    final = run_workflow(state, model=RoleAwareFakeModel())
    assert "analysis_panel" in final["agents_visited"]
    assert "document_retrieval" in final["agents_visited"]
    assert "research" in final["agents_visited"]
    assert "risk" in final["agents_visited"]
    assert "reporter" in final["agents_visited"]
    assert final["risk_verdict"] == "pass"
    assert final.get("report")
    assert final["quant_state"].get("recommended_strategy")
    assert final.get("preliminary_decision")


def test_runner_requires_api_key_without_model(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    result = RuntimeRunner(model=None).run_case(
        {"name": "no_key", "task": "test"},
        write_trace=False,
    )
    assert not result["passed"]
    assert any("DEEPSEEK_API_KEY" in f for f in result["failures"])


def test_runner_with_injected_model():
    result = RuntimeRunner(model=RoleAwareFakeModel()).run_case(
        {
            "name": "mock_case",
            "task": "Ranging market strategy workflow",
            "fixture": "sample_ohlcv.csv",
            "gate": {"expect_report": True},
        },
        write_trace=False,
    )
    assert result["passed"], result["failures"]
    assert result.get("preliminary_decision")
