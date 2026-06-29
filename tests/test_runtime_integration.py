"""Live integration tests — require DEEPSEEK_API_KEY and network.

Run:
  set DEEPSEEK_API_KEY=sk-...
  python -m pytest tests/test_runtime_integration.py -v -m integration
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from quant_agent.agents.llm import has_deepseek_api_key
from quant_agent.runtime.runner import RuntimeRunner

pytestmark = pytest.mark.integration

CASES_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "quant_agent"
    / "harness"
    / "cases"
    / "runtime_cases.yaml"
)


@pytest.fixture(scope="module")
def runtime_cases() -> list[dict]:
    with CASES_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or []


@pytest.mark.skipif(not has_deepseek_api_key(), reason="DEEPSEEK_API_KEY not set")
def test_live_runtime_supervisor_chain(runtime_cases):
    case = next(c for c in runtime_cases if c["name"] == "runtime_supervisor_chain")
    result = RuntimeRunner().run_case(case, write_trace=False)
    assert result["passed"], result["failures"]
    assert result["risk_verdict"] == "pass"
    assert result.get("report")


@pytest.mark.skipif(not has_deepseek_api_key(), reason="DEEPSEEK_API_KEY not set")
def test_live_ad_hoc_task():
    result = RuntimeRunner().run_case(
        {
            "name": "live_ad_hoc",
            "task": (
                "Use get_strategy_recommendation for market_state ranging. "
                "Then ensure risk sizes with kelly method."
            ),
            "gate": {"max_steps": 15, "expect_report": True},
        },
        write_trace=False,
    )
    assert result["agents_visited"]
    assert result.get("report")
