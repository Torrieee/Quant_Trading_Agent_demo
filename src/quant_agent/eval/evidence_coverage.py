"""Evidence coverage: required evidence keys present in final state."""

from __future__ import annotations

from typing import Any


def evaluate_evidence_coverage(
    state: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    required = list(gate.get("required_evidence_keys") or [])
    failures: list[str] = []
    for key in required:
        if key not in state:
            failures.append(f"evidence_coverage: missing key '{key}' in final state")

    failure_types: list[str] = []
    if failures:
        failure_types.append("missing_evidence")

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "failure_types": failure_types,
        "required_keys": required,
        "present_keys": [k for k in required if k in state],
    }
