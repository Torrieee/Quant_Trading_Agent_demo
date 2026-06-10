"""Multi-step tool chain tests for Agent Harness orchestrator (Day 1)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from quant_agent.harness.executor import Executor, resolve_step_arguments
from quant_agent.harness.orchestrator import AgentHarnessOrchestrator
from quant_agent.harness.planner import OfflinePlanner
from quant_agent.harness.tool_adapter import HarnessToolAdapter
from quant_agent.harness.trace import AgentTrace
from quant_agent.llm_agent import TradingFunctionCaller

CASES_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "quant_agent"
    / "harness"
    / "cases"
    / "tool_chain_cases.yaml"
)


@pytest.fixture
def orchestrator() -> AgentHarnessOrchestrator:
    trace_dir = (
        Path(__file__).resolve().parents[1] / "reports" / "test_traces"
    )
    trace_dir.mkdir(parents=True, exist_ok=True)
    return AgentHarnessOrchestrator(
        adapter=HarnessToolAdapter(TradingFunctionCaller()),
        trace_dir=trace_dir,
    )


@pytest.fixture
def chain_cases() -> list[dict]:
    with CASES_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or []


def test_offline_planner_reads_yaml_plan(chain_cases):
    case = next(c for c in chain_cases if c["name"] == "market_to_strategy_chain")
    plan = OfflinePlanner().build_plan(case)
    assert len(plan) == 2
    assert plan[0]["tool"] == "get_strategy_recommendation"
    assert plan[1]["tool"] == "calculate_position_size"


def test_resolve_arguments_from_state():
    state = {"symbol": "AAPL", "position_size": 0.12}
    args = resolve_step_arguments(
        {"arguments": {"method": "kelly"}, "arguments_from_state": {"symbol": "symbol"}},
        state,
    )
    assert args == {"method": "kelly", "symbol": "AAPL"}


def test_market_to_strategy_chain_passes(orchestrator, chain_cases):
    case = next(c for c in chain_cases if c["name"] == "market_to_strategy_chain")
    result = orchestrator.run_case(case, write_trace=False)
    assert result["passed"], result["failures"]
    assert "position_size" in result["final_state"]
    assert result["step_count"] == 2
    assert result["evaluations"]["evidence_coverage"]["passed"]
    trace = result["trace"]
    assert trace["attempt"] == 1
    assert trace["reflection_triggered"] is False
    steps = trace["steps"]
    assert len(steps) == 2
    assert steps[0]["tool_name"] == "get_strategy_recommendation"
    assert steps[0]["status"] == "ok"
    assert steps[1]["tool_name"] == "calculate_position_size"
    assert "rationale" in steps[0]
    assert "latency_ms" in steps[0]


def test_max_steps_limit_fails(orchestrator, chain_cases):
    case = next(c for c in chain_cases if c["name"] == "max_steps_exceeded_should_fail")
    result = orchestrator.run_case(case, write_trace=False)
    assert not result["passed"]
    assert any("max_steps_exceeded" in f for f in result["failures"])


def test_executor_respects_max_steps():
    adapter = HarnessToolAdapter(TradingFunctionCaller())
    trace = AgentTrace.new_root("max_steps_unit")
    executor = Executor(adapter, max_steps=2)
    plan = [
        {"tool": "get_strategy_recommendation", "arguments": {"market_state": "ranging"}},
        {"tool": "get_strategy_recommendation", "arguments": {"market_state": "ranging"}},
        {"tool": "get_strategy_recommendation", "arguments": {"market_state": "ranging"}},
    ]
    _state, errors = executor.run_plan(plan, trace)
    assert errors
    assert any("max_steps_exceeded" in e for e in errors)
    assert len(trace.steps) == 0
