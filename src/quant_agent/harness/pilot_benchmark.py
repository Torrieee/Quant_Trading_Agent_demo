"""Run 4 pilot tasks and aggregate offline evaluation metrics."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .orchestrator import AgentHarnessOrchestrator
from .tool_adapter import HarnessToolAdapter
from ..llm_agent import TradingFunctionCaller

HARNESS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = HARNESS_ROOT.parents[2]
CASES_DIR = HARNESS_ROOT / "cases"


def _load_pilot_cases() -> list[dict[str, Any]]:
    path = CASES_DIR / "pilot_tasks.yaml"
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or []


def _resolve_case_for_mode(case: dict[str, Any], *, live: bool) -> dict[str, Any]:
    resolved = dict(case)
    if case.get("mode") == "offline_or_live":
        if not live:
            offline_plan = case.get("offline_plan")
            if offline_plan:
                resolved["plan"] = offline_plan
        resolved["mode"] = "live" if live else "offline"
    return resolved


def _summarize_task(result: dict[str, Any]) -> dict[str, Any]:
    ev = result.get("evaluations", {})
    eff = ev.get("efficiency", {})
    return {
        "task_id": result["case_id"],
        "passed": result["passed"],
        "tool_correctness": result["passed"],
        "evidence_coverage_pass": ev.get("evidence_coverage", {}).get("passed", True),
        "efficiency": {
            "step_count": eff.get("step_count", 0),
            "total_latency_ms": round(eff.get("total_latency_ms", 0.0), 3),
        },
        "first_attempt_failed": result.get("first_attempt_failed", False),
        "attempt_count": len(result.get("attempts", [])),
        "failures": result.get("failures", []),
    }


def _summarize_judge(judge: dict[str, Any] | None) -> dict[str, Any] | None:
    if not judge:
        return None
    return {
        "judge_mode": judge.get("judge_mode"),
        "model": judge.get("model"),
        "prompt_version": judge.get("prompt_version"),
        "scores": judge.get("scores"),
    }


def run_pilot_benchmark(
    *,
    live: bool = False,
    write_trace: bool = False,
) -> dict[str, Any]:
    orchestrator = AgentHarnessOrchestrator(
        adapter=HarnessToolAdapter(TradingFunctionCaller()),
        live=live,
    )
    tasks: list[dict[str, Any]] = []
    judge_modes: list[str] = []
    for case in _load_pilot_cases():
        resolved = _resolve_case_for_mode(case, live=live)
        result = orchestrator.run_case(resolved, write_trace=write_trace)
        summary = _summarize_task(result)
        if live and result.get("llm_judge"):
            summary["llm_judge"] = _summarize_judge(result["llm_judge"])
            judge_modes.append(result["llm_judge"].get("judge_mode", "unknown"))
        tasks.append(summary)

    total = len(tasks)
    passed = sum(1 for t in tasks if t["passed"])
    tool_ok = sum(1 for t in tasks if t["tool_correctness"])
    evidence_ok = sum(1 for t in tasks if t["evidence_coverage_pass"])

    return {
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if live else "offline",
        "pilot_task_count": total,
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total else 1.0,
            "tool_correctness_rate": tool_ok / total if total else 1.0,
            "evidence_coverage_rate": evidence_ok / total if total else 1.0,
            "reflection_first_attempt_failed_count": sum(
                1 for t in tasks if t["first_attempt_failed"]
            ),
            "llm_judge_live_count": sum(1 for m in judge_modes if m == "live"),
            "llm_judge_fallback_count": sum(
                1 for m in judge_modes if m == "rule_only_fallback"
            ),
        },
        "tasks": tasks,
    }


def write_pilot_report(
    report: dict[str, Any],
    path: Path,
    *,
    is_sample: bool = False,
    sample_note: str | None = None,
) -> None:
    out = dict(report)
    if is_sample:
        out["is_sample"] = True
        out["generated_by"] = "offline demo run"
        out["note"] = sample_note or (
            "Example output for repository display; "
            "rerun scripts/run_pilot_benchmark.py for current results."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def write_pilot_markdown(report: dict[str, Any], path: Path) -> None:
    s = report["summary"]
    lines = [
        "# Pilot Benchmark Summary",
        "",
        f"- Mode: `{report['mode']}`",
        f"- Tasks: {report['pilot_task_count']}",
        f"- Pass rate: {s['pass_rate']:.0%}",
        f"- Tool correctness rate: {s['tool_correctness_rate']:.0%}",
        f"- Evidence coverage rate: {s['evidence_coverage_rate']:.0%}",
        f"- Reflection first-attempt failures: {s['reflection_first_attempt_failed_count']}",
        "",
        "## Per-task",
        "",
        "| task | passed | evidence | steps | latency_ms | first_attempt_failed |",
        "|------|--------|----------|-------|------------|---------------------|",
    ]
    for t in report["tasks"]:
        lines.append(
            f"| {t['task_id']} | {t['passed']} | {t['evidence_coverage_pass']} | "
            f"{t['efficiency']['step_count']} | {t['efficiency']['total_latency_ms']} | "
            f"{t['first_attempt_failed']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_sample_trace_example() -> dict[str, Any]:
    """Representative trace shape for reports/examples (from pilot task 1)."""
    orchestrator = AgentHarnessOrchestrator(
        adapter=HarnessToolAdapter(TradingFunctionCaller()),
    )
    cases = _load_pilot_cases()
    case = next(c for c in cases if c["name"] == "pilot_workflow_report_offline")
    result = orchestrator.run_case(case, write_trace=False)
    trace = dict(result["trace"])
    trace["is_sample"] = True
    trace["note"] = "Example trace; fields illustrate rationale / tool_call / observation."
    return trace
