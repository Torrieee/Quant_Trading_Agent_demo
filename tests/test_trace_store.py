"""Trace store and reflection replay tests (Day 2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from quant_agent.harness.orchestrator import AgentHarnessOrchestrator
from quant_agent.harness.tool_adapter import HarnessToolAdapter
from quant_agent.harness.trace_store import TraceStore
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
def trace_dir() -> Path:
    base = Path(__file__).resolve().parents[1] / "reports" / "test_traces"
    base.mkdir(parents=True, exist_ok=True)
    return base


@pytest.fixture
def orchestrator(trace_dir) -> AgentHarnessOrchestrator:
    return AgentHarnessOrchestrator(
        adapter=HarnessToolAdapter(TradingFunctionCaller()),
        trace_dir=trace_dir,
    )


@pytest.fixture
def chain_cases() -> list[dict]:
    with CASES_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or []


def test_trace_store_save_and_filter(trace_dir):
    store = TraceStore(trace_dir)
    trace = {
        "trace_id": "t1",
        "case_id": "demo_case",
        "attempt": 1,
        "steps": [{"error_type": "tool_error", "status": "failed"}],
    }
    path = store.save(trace)
    assert path.exists()
    found = store.filter(case_id="demo_case", error_type="tool_error")
    assert len(found) == 1
    assert found[0]["trace_id"] == "t1"


def test_evidence_retry_produces_child_trace(orchestrator, chain_cases):
    case = next(c for c in chain_cases if c["name"] == "evidence_retry_chain")
    result = orchestrator.run_case(case)
    assert result["passed"], result["failures"]
    assert result["first_attempt_failed"] is True
    assert len(result["attempts"]) == 2
    assert result["attempts"][0]["passed"] is False
    assert result["attempts"][1]["passed"] is True
    assert result["attempts"][1]["parent_trace_id"] == result["attempts"][0]["trace_id"]
    assert "position_size" in result["final_state"]
    assert result["evaluations"]["evidence_coverage"]["passed"]


def test_replay_trace_from_file(trace_dir, orchestrator, chain_cases):
    case = next(c for c in chain_cases if c["name"] == "market_to_strategy_chain")
    orchestrator.run_case(case)
    trace_path = trace_dir / f"{case['name']}_attempt1.json"
    assert trace_path.exists()

    from quant_agent.harness.replay import replay_trace_file

    replay = replay_trace_file(
        trace_path,
        gate={"required_evidence_keys": ["position_size"]},
    )
    assert replay["passed"]
    assert "position_size" in replay["reconstructed_state_keys"]
