"""披露文本风险关键词与规则标记。"""

from __future__ import annotations

from typing import Any

from .models import EvidenceChunk

# 英文披露关键词（SEC 10-K / 8-K 等）
RISK_PATTERNS: dict[str, list[str]] = {
    "going_concern": ["going concern", "substantial doubt", "持续经营"],
    "bankruptcy": ["bankruptcy", "chapter 11", "破产"],
    "material_weakness": ["material weakness", "internal control", "重大缺陷"],
    "regulatory": ["sec investigation", "regulatory", "subpoena", "监管", "调查"],
    "supply_chain": ["supply chain", "供应链", "single source supplier"],
}


def extract_risk_flags(chunks: list[EvidenceChunk]) -> list[str]:
    """从证据片段中提取风险标记（去重）。"""
    flags: list[str] = []
    combined = " ".join(c.text.lower() for c in chunks)
    for flag, patterns in RISK_PATTERNS.items():
        if any(p.lower() in combined for p in patterns):
            flags.append(flag)
    return flags


def build_document_flags(chunks: list[EvidenceChunk]) -> dict[str, Any]:
    """生成写入 quant_state 的文档规则标记。"""
    flags = extract_risk_flags(chunks)
    severity = "low"
    if any(f in flags for f in ("going_concern", "bankruptcy")):
        severity = "high"
    elif flags:
        severity = "medium"
    return {
        "risk_flags": flags,
        "event_severity": severity,
        "chunk_count": len(chunks),
    }
