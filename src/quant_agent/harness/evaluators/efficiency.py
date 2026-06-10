"""Efficiency metrics: step_count and latency (latency is report-only by default)."""

from __future__ import annotations

from typing import Any

from ..trace import AgentTraceRecord


def _step_latency(step: AgentTraceRecord | dict[str, Any]) -> float:
    if isinstance(step, AgentTraceRecord):
        return step.latency_ms
    return float(step.get("latency_ms", 0.0))


def evaluate_efficiency(
    steps: list[AgentTraceRecord] | list[dict[str, Any]],
    gate: dict[str, Any],
    *,
    exec_errors: list[str] | None = None,
) -> dict[str, Any]:
    step_count = len(steps)
    total_latency_ms = sum(_step_latency(s) for s in steps)
    failures: list[str] = list(exec_errors or [])

    gate_max_executed = gate.get("gate_max_executed_steps")
    if gate_max_executed is not None and step_count > gate_max_executed:
        failures.append(
            f"efficiency: step_count {step_count} exceeds gate_max_executed_steps "
            f"{gate_max_executed}"
        )

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "step_count": step_count,
        "total_latency_ms": total_latency_ms,
        "latency_gated": False,
        "checks": {
            "step_count_reported": True,
            "latency_report_only": True,
        },
    }
