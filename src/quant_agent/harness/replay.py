"""Replay stored traces through offline evaluators."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evaluators.efficiency import evaluate_efficiency
from .evaluators.evidence_coverage import evaluate_evidence_coverage
from .executor import merge_observation_into_state


def reconstruct_state_from_trace(trace: dict[str, Any]) -> dict[str, Any]:
    state: dict[str, Any] = {}
    for step in trace.get("steps") or []:
        if step.get("status") == "ok":
            obs = step.get("observation")
            if isinstance(obs, dict):
                merge_observation_into_state(state, obs)
    return state


def replay_trace_data(trace: dict[str, Any], gate: dict[str, Any] | None = None) -> dict[str, Any]:
    gate = gate or {}
    state = reconstruct_state_from_trace(trace)
    evidence = evaluate_evidence_coverage(state, gate)
    efficiency = evaluate_efficiency(trace.get("steps") or [], gate)
    passed = evidence["passed"] and efficiency["passed"]
    return {
        "case_id": trace.get("case_id"),
        "attempt": trace.get("attempt"),
        "passed": passed,
        "evidence_coverage": evidence,
        "efficiency": efficiency,
        "reconstructed_state_keys": list(state.keys()),
    }


def replay_trace_file(path: Path, gate: dict[str, Any] | None = None) -> dict[str, Any]:
    trace = json.loads(path.read_text(encoding="utf-8"))
    result = replay_trace_data(trace, gate)
    result["trace_file"] = str(path)
    return result
