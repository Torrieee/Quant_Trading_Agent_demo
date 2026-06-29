"""Research 动态子图：证据与产出验证。"""

from __future__ import annotations

from typing import Any


def verify_research(state: dict[str, Any]) -> dict[str, Any]:
    """规则 Verifier：检查 findings 与 quant_state 是否满足计划要求。"""
    plan = list(state.get("research_plan") or [])
    findings = list(state.get("research_findings") or [])
    quant = dict(state.get("quant_state") or {})
    missing: list[str] = []
    conflicts: list[str] = []

    workers_done = {f.get("worker") for f in findings}

    for task in plan:
        worker = task.get("worker")
        if worker not in workers_done:
            missing.append(f"缺少 worker: {worker}")
            continue
        finding = next((f for f in findings if f.get("worker") == worker), None)
        if not finding:
            continue
        if finding.get("status") != "ok":
            missing.append(f"{worker} 执行失败")
        if task.get("required_evidence") and not finding.get("evidence_ids"):
            missing.append(f"{worker} 缺少 evidence_ids")

    if "strategy" in workers_done and not quant.get("recommended_strategy"):
        missing.append("未写入 recommended_strategy")

    if quant.get("risk_flags") and plan:
        ev_findings = [f for f in findings if f.get("worker") == "evidence"]
        if any(t.get("worker") == "evidence" for t in plan) and ev_findings:
            if not any(f.get("evidence_ids") for f in ev_findings):
                missing.append("存在 risk_flags 但 evidence 未引用文档")

    passed = len(missing) == 0

    gate = state.get("gate") or {}
    if gate.get("force_research_replan_once") and int(state.get("replan_count") or 0) == 0:
        passed = False
        missing.append("showcase: 首次 verifier 故意失败以演示 replan")

    return {
        "passed": passed,
        "missing": missing,
        "conflicts": conflicts,
    }
