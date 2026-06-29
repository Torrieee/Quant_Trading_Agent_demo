"""失败分类：将 failures / trace 事件映射为 failure tag。"""

from __future__ import annotations

from typing import Any

_RULES: list[tuple[str, str]] = [
    ("缺少预期智能体", "orchestration_skip"),
    ("缺少报告", "orchestration_skip"),
    ("risk_flags", "evidence_miss"),
    ("document_signal", "document_signal_skip"),
    ("episodic_memory", "memory_miss"),
    ("未调用工具", "tool_missing"),
    ("risk_verdict", "risk_false_pass"),
    ("风控拒绝", "risk_false_reject"),
    ("position_size", "risk_false_reject"),
    ("interrupted", "hitl_break"),
    ("HITL", "hitl_break"),
    ("confidence", "grounding_fail"),
    ("DEEPSEEK_API_KEY", "api_error"),
    ("tool_timeout", "tool_timeout"),
    ("research_verify", "verifier_fail"),
    ("verifier", "verifier_fail"),
    ("replan", "replan"),
    ("retry", "tool_retry"),
    ("step_failed", "runtime_error"),
]


def classify_failures(failures: list[str]) -> list[str]:
    tags: list[str] = []
    for msg in failures:
        matched = False
        for needle, tag in _RULES:
            if needle in msg:
                if tag not in tags:
                    tags.append(tag)
                matched = True
                break
        if not matched and msg:
            if "efficiency" in msg and "step_count" not in msg:
                continue
            if "unknown" not in tags:
                tags.append("other")
    return tags or (["unknown"] if failures else [])


def classify_trace_events(trace_steps: list[dict[str, Any]]) -> list[str]:
    """从 trace_steps 提取可聚类事件标签（成功路径也统计）。"""
    events: list[str] = []
    for step in trace_steps:
        if not isinstance(step, dict):
            continue
        agent = str(step.get("agent") or "")
        tool = str(step.get("tool_name") or "")
        obs = step.get("observation") or {}
        if not isinstance(obs, dict):
            obs = {}

        if step.get("status") == "failed" or obs.get("error"):
            err = str(obs.get("error") or step.get("error_type") or "error")
            if "timeout" in err.lower():
                events.append("tool_timeout")
            else:
                events.append("tool_error")

        retry = int(obs.get("retry_count") or 0)
        if retry > 0:
            events.append("tool_retry")

        if agent == "research_verifier" and obs.get("passed") is False:
            events.append("verifier_fail")
        if agent == "research_replan_bump" or tool == "replan_bump":
            events.append("replan")
        if agent == "research_planner" and int((step.get("arguments") or {}).get("replan_count") or 0) > 0:
            events.append("replan")
        if step.get("parallel"):
            events.append("parallel_worker")
        if step.get("hitl") or tool == "human_approval":
            events.append("hitl_interrupt")
        if tool == "human_approval_resume":
            events.append("hitl_resume")

    seen: set[str] = set()
    out: list[str] = []
    for e in events:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out
