"""Phase-level process trace for TradingAgent pipeline."""

from __future__ import annotations

from typing import Any

from ...agent import TradingAgent


def build_process_trace(agent: TradingAgent, case_id: str) -> dict[str, Any]:
    """Run perceive→decide→act→evaluate and record phase-level trace."""
    trace: dict[str, Any] = {
        "case_id": case_id,
        "steps": [],
        "final_metrics": {},
        "errors": [],
    }

    def _step(phase: str, status: str, output_keys: list[str], error: str | None = None):
        step = {"phase": phase, "status": status, "output_keys": output_keys}
        trace["steps"].append(step)
        if error:
            trace["errors"].append(error)

    try:
        data = agent.perceive()
        _step(
            "perceive",
            "passed",
            [
                "data_shape",
                "symbol",
                "date_range",
            ],
        )
        trace["_perceive_meta"] = {
            "data_shape": list(data.shape),
            "symbol": agent.config.data.symbol,
            "date_range": [str(data.index[0]), str(data.index[-1])],
        }

        strategy_result = agent.decide()
        _step(
            "decide",
            "passed",
            ["strategy_name", "signal_col"],
        )
        trace["_decide_meta"] = {
            "strategy_name": agent.config.strategy.name,
            "signal_col": strategy_result.signal_col,
        }

        backtest_result = agent.act()
        _step(
            "act",
            "passed",
            ["equity_curve_col", "has_backtest_data"],
        )
        trace["_act_meta"] = {
            "equity_curve_col": backtest_result.equity_curve_col,
            "has_backtest_data": backtest_result.data is not None
            and len(backtest_result.data) > 0,
        }

        stats = agent.evaluate()
        _step("evaluate", "passed", ["stats"])
        trace["final_metrics"] = stats

    except Exception as exc:
        _step("unknown", "failed", [], str(exc))

    return trace


def validate_process_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Validate phase trace structure for quality gate."""
    failures: list[str] = []
    expected_phases = ["perceive", "decide", "act", "evaluate"]
    steps = trace.get("steps", [])
    phases = [s.get("phase") for s in steps]

    for phase in expected_phases:
        if phase not in phases:
            failures.append(f"pipeline_completed: missing phase '{phase}'")
            continue
        step = next(s for s in steps if s.get("phase") == phase)
        if step.get("status") != "passed":
            failures.append(f"pipeline_completed: phase '{phase}' not passed")
        if not step.get("output_keys"):
            failures.append(f"step_output_keys_present: '{phase}' has empty output_keys")

    if trace.get("errors"):
        failures.append(f"pipeline_completed: errors present: {trace['errors']}")

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "checks": {
            "pipeline_completed": not any("pipeline_completed" in f for f in failures),
            "step_output_keys_present": not any(
                "step_output_keys_present" in f for f in failures
            ),
        },
    }
