"""扩展 code grader：expect 块断言。"""

from __future__ import annotations

from typing import Any


def evaluate_expectations(
    result: dict[str, Any],
    expect: dict[str, Any],
) -> dict[str, Any]:
    """对 RuntimeRunner 结果执行 expect 断言。"""
    failures: list[str] = []
    final_state = result.get("final_state") or {}
    decision = result.get("preliminary_decision") or final_state.get("preliminary_decision") or {}
    trace_steps = result.get("trace", {}).get("steps") or []

    for flag in expect.get("risk_flags_contains") or []:
        flags = list(final_state.get("risk_flags") or [])
        if flag not in flags:
            failures.append(f"expect: risk_flags 缺少 '{flag}' (got {flags})")

    if expect.get("document_signal_applied") is True:
        doc_sig = final_state.get("document_signal") or decision.get("document_signal") or {}
        if not doc_sig.get("applied"):
            failures.append("expect: document_signal 未应用")

    if expect.get("document_signal_applied") is False:
        doc_sig = final_state.get("document_signal") or decision.get("document_signal") or {}
        if doc_sig.get("applied"):
            failures.append("expect: document_signal 不应被应用")

    cap_map = expect.get("max_confidence_if_flags") or {}
    for flag, cap in cap_map.items():
        flags = list(final_state.get("risk_flags") or [])
        if flag in flags:
            conf = decision.get("confidence")
            if conf is None:
                failures.append(f"expect: 存在 {flag} 但缺少 confidence")
            elif float(conf) > float(cap):
                failures.append(
                    f"expect: {flag} 时 confidence {conf} 超过上限 {cap}"
                )

    for tool in expect.get("required_tools") or []:
        tools_called = {
            s.get("tool_name")
            for s in trace_steps
            if isinstance(s, dict)
        }
        if tool not in tools_called:
            failures.append(f"expect: trace 未调用工具 '{tool}'")

    if expect.get("episodic_memory_nonempty"):
        episodic = final_state.get("episodic_memory") or []
        if not episodic:
            failures.append("expect: episodic_memory 为空")

    expected_verdict = expect.get("risk_verdict")
    if expected_verdict is not None:
        if result.get("risk_verdict") != expected_verdict:
            failures.append(
                f"expect: risk_verdict 期望 {expected_verdict}，"
                f"实际 {result.get('risk_verdict')}"
            )

    if expect.get("interrupted") is True and not result.get("interrupted"):
        failures.append("expect: 应处于 HITL interrupt 状态")

    if expect.get("interrupted") is False and result.get("interrupted"):
        failures.append("expect: 不应处于 interrupt 状态")

    forbidden_signal = expect.get("forbidden_signal")
    if forbidden_signal:
        sig = str(decision.get("signal_type", "")).lower()
        if sig == str(forbidden_signal).lower():
            failures.append(f"expect: signal_type 不应为 {forbidden_signal}")

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "checks_run": list(expect.keys()),
    }
