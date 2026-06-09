"""Tool schema contract tests — core highlight for quality/efficiency role."""

import pytest

from quant_agent.harness.evaluators.tool_compliance import (
    run_tool_compliance_checks,
    validate_tool_schemas,
)
from quant_agent.llm_agent import TradingFunctionCaller


@pytest.fixture
def caller() -> TradingFunctionCaller:
    return TradingFunctionCaller()


def test_schema_fields_and_required_present(caller):
    result = validate_tool_schemas(caller.get_available_functions())
    assert result["passed"], result["failures"]
    assert result["checks"]["schema_fields_present"]
    assert result["checks"]["required_args_present"]


def test_enum_values_valid(caller):
    result = validate_tool_schemas(caller.get_available_functions())
    assert result["checks"]["enum_values_valid"], result["failures"]


def test_get_strategy_recommendation_valid_routing(caller):
    case = {
        "name": "valid_ranging",
        "tool": "get_strategy_recommendation",
        "arguments": {"market_state": "ranging"},
        "gate": {"expected_keys": ["recommended_strategy", "reason"]},
    }
    result = run_tool_compliance_checks(caller, case)
    assert result["passed"], result["failures"]


def test_invalid_enum_returns_clear_error(caller):
    case = {
        "name": "invalid_enum",
        "tool": "get_strategy_recommendation",
        "arguments": {"market_state": "invalid_state"},
        "gate": {"expect_error": True},
    }
    result = run_tool_compliance_checks(caller, case)
    assert result["passed"], result["failures"]
    assert "error" in result["result"]


def test_invalid_method_returns_clear_error(caller):
    case = {
        "name": "invalid_method",
        "tool": "calculate_position_size",
        "arguments": {"method": "unknown_method"},
        "gate": {"expect_error": True},
    }
    result = run_tool_compliance_checks(caller, case)
    assert result["passed"], result["failures"]
