"""Pilot benchmark tests (Day 3 MVP — offline, no API)."""

from __future__ import annotations

from pathlib import Path

import yaml

from quant_agent.harness.pilot_benchmark import run_pilot_benchmark

CASES_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "quant_agent"
    / "harness"
    / "cases"
    / "pilot_tasks.yaml"
)


def test_pilot_tasks_yaml_has_four_offline_baselines():
    with CASES_PATH.open(encoding="utf-8") as fh:
        cases = yaml.safe_load(fh) or []
    assert len(cases) == 4
    for case in cases:
        assert case.get("plan") or case.get("offline_plan"), case["name"]


def test_pilot_benchmark_offline_runs_all_four():
    report = run_pilot_benchmark(live=False, write_trace=False)
    assert report["pilot_task_count"] == 4
    assert report["mode"] == "offline"
    assert report["summary"]["passed"] == 4
    assert report["summary"]["tool_correctness_rate"] == 1.0
    assert report["summary"]["evidence_coverage_rate"] == 1.0
    assert report["summary"]["reflection_first_attempt_failed_count"] == 1
    ids = {t["task_id"] for t in report["tasks"]}
    assert ids == {
        "pilot_workflow_report_offline",
        "pilot_market_strategy_offline",
        "pilot_volatility_sizing_offline_or_live",
        "pilot_evidence_repair_offline_or_live",
    }
