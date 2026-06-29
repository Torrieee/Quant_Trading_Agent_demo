"""Research 动态子图：合并 findings 写入 quant_state。"""

from __future__ import annotations

from typing import Any


def synthesize_research(state: dict[str, Any]) -> dict[str, Any]:
    """将 findings 汇总为 research_summary 并确保关键字段存在。"""
    quant = dict(state.get("quant_state") or {})
    findings = list(state.get("research_findings") or [])
    verification = dict(state.get("research_verification") or {})

    lines = []
    for f in findings:
        lines.append(
            f"- [{f.get('worker')}] {f.get('claim')} "
            f"(conf={f.get('confidence')}, evidence={f.get('evidence_ids')})"
        )
    quant["research_findings"] = findings
    quant["research_summary"] = "\n".join(lines) if lines else "无研究产出"
    quant["research_verification"] = verification

    if not quant.get("recommended_strategy"):
        for f in findings:
            if f.get("worker") == "strategy" and "mean_reversion" in str(f.get("claim", "")):
                quant.setdefault("recommended_strategy", "mean_reversion")
            if f.get("worker") == "strategy" and "momentum" in str(f.get("claim", "")):
                quant.setdefault("recommended_strategy", "momentum")

    return quant
