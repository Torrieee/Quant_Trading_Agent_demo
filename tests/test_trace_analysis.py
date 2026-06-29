"""Trace 分析与 showcase 测试。"""

from __future__ import annotations

import shutil
from pathlib import Path

from quant_agent.eval.taxonomy import classify_trace_events
from quant_agent.observability.trace_analysis import analyze_traces, ingest_eval_failure

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRACE_TMP = PROJECT_ROOT / "tests" / "_trace_tmp"


def test_classify_trace_events_showcase_sequence():
    steps = [
        {"agent": "research_evidence", "observation": {"retry_count": 1}, "parallel": True},
        {"agent": "research_verifier", "observation": {"passed": False}},
        {"agent": "research_replan_bump", "tool_name": "replan_bump"},
        {"agent": "hitl", "tool_name": "human_approval", "hitl": True},
        {"agent": "hitl", "tool_name": "human_approval_resume"},
    ]
    events = classify_trace_events(steps)
    assert "tool_retry" in events
    assert "verifier_fail" in events
    assert "replan" in events
    assert "hitl_interrupt" in events
    assert "hitl_resume" in events


def test_analyze_traces_empty_dir():
    TRACE_TMP.mkdir(parents=True, exist_ok=True)
    try:
        report = analyze_traces(TRACE_TMP)
        assert report["summary"]["trace_count"] == 0
    finally:
        if TRACE_TMP.exists():
            shutil.rmtree(TRACE_TMP, ignore_errors=True)


def test_ingest_eval_failure_writes_trace(monkeypatch):
    TRACE_TMP.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_TRACE_DIR", str(TRACE_TMP))
    try:
        out = ingest_eval_failure(
            case_id="demo_fail",
            failures=["未调用工具 'foo'"],
            trace_steps=[{"agent": "research", "tool_name": "x", "status": "failed"}],
            extra={"symbol": "FIXTURE"},
        )
        assert "tool_missing" in out["failure_tags"]
        assert Path(out["trace_path"]).is_file()
    finally:
        if TRACE_TMP.exists():
            shutil.rmtree(TRACE_TMP, ignore_errors=True)
