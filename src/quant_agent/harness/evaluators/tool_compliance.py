"""Tool schema contract checks for TradingFunctionCaller."""

from __future__ import annotations

from typing import Any

from ...llm_agent import TradingFunctionCaller


def validate_tool_schemas(functions: list[dict[str, Any]]) -> dict[str, Any]:
    """Run schema-level checks on all registered tools."""
    failures: list[str] = []

    for fn in functions:
        name = fn.get("name", "<unknown>")

        for field in ("name", "description", "parameters"):
            if field not in fn or fn[field] in (None, ""):
                failures.append(
                    f"schema_fields_present: tool '{name}' missing '{field}'"
                )

        params = fn.get("parameters", {})
        properties = params.get("properties", {})
        required = params.get("required", [])

        if "required" not in params:
            failures.append(
                f"required_args_present: tool '{name}' missing parameters.required"
            )
        else:
            for req in required:
                if req not in properties:
                    failures.append(
                        f"required_args_present: tool '{name}' required '{req}' "
                        "not in properties"
                    )

        for prop_name, prop_def in properties.items():
            enum_vals = prop_def.get("enum")
            if enum_vals is not None:
                if not enum_vals or not all(isinstance(v, str) for v in enum_vals):
                    failures.append(
                        f"enum_values_valid: tool '{name}' property '{prop_name}' "
                        "has invalid enum"
                    )

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "checks": {
            "schema_fields_present": not any(
                "schema_fields_present" in f for f in failures
            ),
            "required_args_present": not any(
                "required_args_present" in f for f in failures
            ),
            "enum_values_valid": not any("enum_values_valid" in f for f in failures),
        },
    }


def run_tool_compliance_checks(
    caller: TradingFunctionCaller,
    case: dict[str, Any],
) -> dict[str, Any]:
    """Run per-case tool call checks (mock routing + negative cases)."""
    failures: list[str] = []
    tool_name = case["tool"]
    arguments = case.get("arguments", {})
    gate = case.get("gate", {})
    expect_error = gate.get("expect_error", False)
    expected_keys = gate.get("expected_keys", [])

    try:
        result = caller.call_function(tool_name, arguments)
    except Exception as exc:
        if expect_error:
            return {
                "passed": True,
                "failures": [],
                "result": {"error": str(exc)},
                "checks": {
                    "mock_arguments_parseable": True,
                    "handler_returns_expected_keys": True,
                    "invalid_arguments_raise_clear_error": True,
                },
            }
        failures.append(f"mock_arguments_parseable: unexpected exception: {exc}")
        result = {"error": str(exc)}
    else:
        if expect_error:
            if not isinstance(result, dict) or "error" not in result:
                failures.append(
                    "invalid_arguments_raise_clear_error: expected error response"
                )
        else:
            if isinstance(result, dict) and "error" in result:
                failures.append(
                    f"mock_arguments_parseable: handler returned error: {result['error']}"
                )
            for key in expected_keys:
                if not isinstance(result, dict) or key not in result:
                    failures.append(
                        f"handler_returns_expected_keys: missing '{key}' in result"
                    )

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "result": result,
        "checks": {
            "mock_arguments_parseable": not any(
                "mock_arguments_parseable" in f for f in failures
            ),
            "handler_returns_expected_keys": not any(
                "handler_returns_expected_keys" in f for f in failures
            ),
            "invalid_arguments_raise_clear_error": not any(
                "invalid_arguments_raise_clear_error" in f for f in failures
            ),
        },
    }
