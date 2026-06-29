"""Trace 在线分析：失败聚类、taxonomy 归因、产品闭环报告。"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..eval.taxonomy import classify_failures, classify_trace_events

DEFAULT_TRACE_DIR = Path("data_cache/traces")
DEFAULT_REPORT_PATH = Path("reports/trace_insights.json")


def _load_trace_files(trace_dir: Path) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    if not trace_dir.is_dir():
        return traces
    for path in sorted(trace_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        data["_source_path"] = str(path)
        traces.append(data)
    return traces


def _trace_failures(trace: dict[str, Any]) -> list[str]:
    failures: list[str] = list(trace.get("failures") or [])
    extra = trace.get("extra") or {}
    if isinstance(extra.get("failures"), list):
        failures.extend(str(x) for x in extra["failures"])
    fs = trace.get("final_state") or {}
    for step in trace.get("trace_steps") or trace.get("steps") or []:
        if not isinstance(step, dict):
            continue
        if step.get("status") == "failed":
            failures.append(
                f"step_failed: {step.get('agent')}/{step.get('tool_name')} "
                f"({step.get('error_type') or step.get('observation', {}).get('error', 'unknown')})"
            )
    if trace.get("success") is False and trace.get("error"):
        failures.append(str(trace["error"]))
    if extra.get("interrupted") and not trace.get("report"):
        failures.append("interrupted: HITL 未完成 resume")
    return failures


def analyze_traces(
    trace_dir: Path | str | None = None,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    """扫描 trace 目录，输出聚类与归因报告。"""
    root = Path(trace_dir or DEFAULT_TRACE_DIR)
    traces = _load_trace_files(root)
    if limit:
        traces = traces[-limit:]

    event_counter: Counter[str] = Counter()
    failure_tag_counter: Counter[str] = Counter()
    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    case_rows: list[dict[str, Any]] = []

    for trace in traces:
        case_id = trace.get("case_id") or "unknown"
        symbol = trace.get("symbol") or ""
        steps = trace.get("trace_steps") or trace.get("steps") or []
        events = classify_trace_events(steps)
        for ev in events:
            event_counter[ev] += 1

        failures = _trace_failures(trace)
        tags = classify_failures(failures)
        for tag in tags:
            failure_tag_counter[tag] += 1
            clusters[tag].append(
                {
                    "case_id": case_id,
                    "symbol": symbol,
                    "source": trace.get("_source_path"),
                    "failures": failures[:5],
                }
            )

        case_rows.append(
            {
                "case_id": case_id,
                "symbol": symbol,
                "step_count": len(steps),
                "events": events,
                "failure_tags": tags,
                "has_failures": bool(failures),
                "showcase": bool((trace.get("extra") or {}).get("showcase")),
                "source": trace.get("_source_path"),
            }
        )

    total = len(traces)
    failed = sum(1 for r in case_rows if r["has_failures"])
    top_tags = failure_tag_counter.most_common(8)
    top_events = event_counter.most_common(12)

    recommendations = _recommendations(top_tags, top_events)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trace_dir": str(root),
        "summary": {
            "trace_count": total,
            "traces_with_failures": failed,
            "failure_rate": round(failed / total, 3) if total else 0.0,
            "top_failure_tags": [{"tag": t, "count": c} for t, c in top_tags],
            "top_events": [{"event": e, "count": c} for e, c in top_events],
        },
        "clusters": {k: v[:20] for k, v in clusters.items()},
        "cases": case_rows,
        "recommendations": recommendations,
    }


def _recommendations(
    top_tags: list[tuple[str, int]],
    top_events: list[tuple[str, int]],
) -> list[str]:
    recs: list[str] = []
    tag_set = {t for t, _ in top_tags}
    event_set = {e for e, _ in top_events}
    if "tool_timeout" in event_set or "tool_retry" in event_set:
        recs.append("检查 ToolExecutionPolicy.max_retries 与 timeout；在 reliability_v1 保持故障注入回归。")
    if "verifier_fail" in event_set or "replan" in event_set:
        recs.append("Review 子图 Verifier 规则与 max_replan；确保 replan 后 evidence worker 补齐。")
    if "hitl_break" in tag_set or "hitl_interrupt" in event_set:
        recs.append("HITL 中断后确认 thread_id 一致并 resume；生产可升级为节点内 interrupt()。")
    if "orchestration_skip" in tag_set:
        recs.append("检查 expected_agents 与 Supervisor 路由条件是否过早终止。")
    if "tool_missing" in tag_set:
        recs.append("放宽 Live eval 的 required_tools，改用 at_least_one_of_tools 里程碑断言。")
    if not recs:
        recs.append("近期 trace 无显著失败聚类；可运行 showcase_resilience 生成演示链路。")
    return recs


def write_trace_insights_report(
    report: dict[str, Any],
    path: Path | str = DEFAULT_REPORT_PATH,
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md = out.with_suffix(".md")
    md.write_text(_report_to_markdown(report), encoding="utf-8")
    return out


def _report_to_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Trace Insights",
        "",
        f"- 生成时间: {report['generated_at']}",
        f"- Trace 数: {s['trace_count']}",
        f"- 含失败/异常: {s['traces_with_failures']} ({s['failure_rate']:.0%})",
        "",
        "## 失败 Tag 聚类",
        "",
    ]
    for item in s.get("top_failure_tags") or []:
        lines.append(f"- `{item['tag']}`: {item['count']}")
    lines.extend(["", "## 事件统计", ""])
    for item in s.get("top_events") or []:
        lines.append(f"- `{item['event']}`: {item['count']}")
    lines.extend(["", "## 闭环建议", ""])
    for r in report.get("recommendations") or []:
        lines.append(f"- {r}")
    lines.append("")
    return "\n".join(lines)


def ingest_eval_failure(
    *,
    case_id: str,
    failures: list[str],
    trace_steps: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Eval 失败时写入轻量 trace 并返回归因（供 runner 闭环）。"""
    tags = classify_failures(failures)
    events = classify_trace_events(trace_steps or [])
    payload = {
        "case_id": case_id,
        "symbol": (extra or {}).get("symbol", "FIXTURE"),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "trace_steps": trace_steps or [],
        "failures": failures,
        "extra": {
            **(extra or {}),
            "source": "eval_runner",
            "failure_tags": tags,
            "events": events,
        },
    }
    from .tracer import export_trace

    path = export_trace(
        case_id=f"eval_fail_{case_id}",
        symbol=payload["symbol"],
        trace_steps=trace_steps or [],
        final_state={},
        extra=payload["extra"],
    )
    return {"failure_tags": tags, "events": events, "trace_path": str(path)}
