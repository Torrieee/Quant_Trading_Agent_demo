"""工具策略与可靠性评测测试。"""

from __future__ import annotations

from pathlib import Path

from quant_agent.eval.reliability import pass_pow_k, run_reliability_eval
from quant_agent.runtime.tool_adapter import HarnessToolAdapter
from quant_agent.runtime.tool_policy import ToolExecutionPolicy
from quant_agent.runtime.trace import ToolCallRequest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_tool_fault_injection_retries():
    adapter = HarnessToolAdapter(
        policy=ToolExecutionPolicy(max_retries=2),
    )
    adapter.set_fault_injection(
        {
            "type": "tool_timeout",
            "tool_name": "get_strategy_recommendation",
            "fail_count": 1,
            "error_code": "tool_timeout",
        }
    )
    # 第一次注入失败并重试，第二次应成功（真实工具调用）
    result = adapter.invoke_with_policy(
        ToolCallRequest(
            name="get_strategy_recommendation",
            arguments={"market_state": "ranging", "symbol": "FIXTURE"},
        )
    )
    assert result.ok
    assert result.retry_count >= 1


def test_pass_pow_k():
    assert pass_pow_k([True, True, True], 3) == 1.0
    assert pass_pow_k([True, False, True], 3) == 0.0


def test_run_reliability_eval_offline():
    report = run_reliability_eval(PROJECT_ROOT / "evalsets" / "reliability_v1.yaml")
    assert report["benchmark"]["passed"] is True
    assert report["eval_focus"] == "fault_recovery"
    assert report["summary"]["passed_cases"] == report["summary"]["total_cases"]
