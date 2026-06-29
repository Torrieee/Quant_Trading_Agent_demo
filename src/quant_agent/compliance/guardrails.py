"""输出与决策 guardrails。"""

from __future__ import annotations

import re
from typing import Any

# 禁止在报告中出现的绝对化投资建议措辞（合规提示）
_FORBIDDEN_PATTERNS = [
    re.compile(r"(?i)guaranteed\s+profit"),
    re.compile(r"(?i)无风险"),
    re.compile(r"(?i)一定涨"),
    re.compile(r"(?i)100%\s*return"),
]


def sanitize_report_text(report: str | None) -> str | None:
    if not report:
        return report
    out = report
    for pat in _FORBIDDEN_PATTERNS:
        out = pat.sub("[已过滤不合规表述]", out)
    if "免责声明" not in out and "disclaimer" not in out.lower():
        out += (
            "\n\n---\n免责声明：本报告由 AI 生成，仅供研究参考，不构成投资建议。"
            " past performance 不保证 future results。"
        )
    return out


def validate_decision(decision: dict[str, Any]) -> list[str]:
    """返回合规警告列表（不阻断流程）。"""
    warnings: list[str] = []
    conf = float(decision.get("confidence") or 0)
    if conf > 95:
        warnings.append("confidence 过高，建议人工复核")
    sig = str(decision.get("signal_type", "")).lower()
    doc = decision.get("document_signal") or {}
    if sig == "buy" and doc.get("event_severity") == "high":
        warnings.append("高风险披露下仍建议买入，需人工确认")
    flags = doc.get("risk_flags") or decision.get("risk_flags") or []
    if sig == "buy" and "going_concern" in flags:
        warnings.append("going_concern 标记下买入信号异常")
    return warnings
