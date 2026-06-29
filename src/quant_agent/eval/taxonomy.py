"""失败分类：将 failures 映射为 failure tag。"""

from __future__ import annotations

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
    ("confidence", "grounding_fail"),
    ("DEEPSEEK_API_KEY", "api_error"),
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
