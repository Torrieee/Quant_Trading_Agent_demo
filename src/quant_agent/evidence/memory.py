"""Episodic Memory：跨次 analyze 的结构化会话记忆。"""

from __future__ import annotations

import datetime as dt
import os
import re
from typing import Any

from .models import EvidenceChunk

EPISODIC_DOC_TYPES = frozenset({"episodic_memory", "internal_analysis"})
EPISODIC_SOURCES = frozenset({"engine_feedback", "episodic_memory"})

MAX_EPISODIC_PER_SYMBOL = int(os.environ.get("EVIDENCE_MAX_EPISODIC", "20"))


def is_episodic_chunk(chunk: EvidenceChunk) -> bool:
    return chunk.doc_type in EPISODIC_DOC_TYPES or chunk.source in EPISODIC_SOURCES


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_") or "entry"


def _dedupe_chunks(chunks: list[EvidenceChunk]) -> list[EvidenceChunk]:
    seen: set[str] = set()
    out: list[EvidenceChunk] = []
    for c in chunks:
        if c.doc_id in seen:
            continue
        seen.add(c.doc_id)
        out.append(c)
    return out


def build_episodic_chunk(
    symbol: str,
    *,
    case_id: str,
    task: str,
    decision: dict[str, Any],
    risk_verdict: str | None,
    risk_reason: str | None,
    report: str | None,
    final_state: dict[str, Any] | None = None,
    analyzed_at: str | None = None,
) -> EvidenceChunk:
    """从一次 Engine 分析结果构建结构化 episodic memory。"""
    ts = analyzed_at or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    signal = decision.get("signal_type", "unknown")
    confidence = decision.get("confidence", "—")
    strategy = (final_state or {}).get("recommended_strategy", "—")
    risk_flags = (final_state or {}).get("risk_flags") or []

    report_excerpt = (report or "")[:1500]
    reasoning = decision.get("reasoning", "")
    if isinstance(reasoning, str) and len(reasoning) > 400:
        reasoning = reasoning[:400] + "..."

    text = (
        f"Episodic analysis memory for {symbol.upper()} at {ts}.\n"
        f"Case: {case_id}\n"
        f"Task: {task[:300]}\n"
        f"Decision: {signal} (confidence {confidence}%)\n"
        f"Recommended strategy: {strategy}\n"
        f"Risk verdict: {risk_verdict or 'unknown'}"
        + (f" — {risk_reason}" if risk_reason else "")
        + "\n"
        f"Risk flags from evidence: {', '.join(risk_flags) if risk_flags else 'none'}\n"
        f"Panel reasoning summary: {reasoning or 'n/a'}\n"
        f"Report excerpt:\n{report_excerpt}"
    )

    doc_id = f"{symbol.upper()}_episodic_{_slug(case_id)}_{_slug(ts)}"
    return EvidenceChunk(
        doc_id=doc_id,
        text=text,
        symbol=symbol.upper(),
        doc_type="episodic_memory",
        source="episodic_memory",
        title=f"{symbol.upper()} analysis @ {ts}",
        published_at=ts,
        section="episodic_session",
    )


def merge_chunk_lists(
    existing: list[EvidenceChunk],
    fresh: list[EvidenceChunk],
) -> list[EvidenceChunk]:
    """
    合并索引：
    - episodic（existing + fresh）保留，按时间截断
    - profile / SEC 从 fresh 刷新；无新 SEC 时保留旧 SEC 或 seed
    """
    episodic = [c for c in existing if is_episodic_chunk(c)]
    episodic.extend(c for c in fresh if is_episodic_chunk(c))
    episodic.sort(key=lambda c: c.published_at or "", reverse=True)
    episodic = _dedupe_chunks(episodic)[:MAX_EPISODIC_PER_SYMBOL]

    fresh_external = [c for c in fresh if not is_episodic_chunk(c)]
    fresh_sec = [c for c in fresh_external if c.source == "sec_edgar"]
    fresh_profile = [c for c in fresh_external if c.doc_type == "profile"]
    fresh_seed = [c for c in fresh_external if c.source == "seed"]
    fresh_other = [
        c
        for c in fresh_external
        if c not in fresh_sec and c not in fresh_profile and c not in fresh_seed
    ]

    old_external = [c for c in existing if not is_episodic_chunk(c)]
    old_sec = [c for c in old_external if c.source == "sec_edgar"]
    old_other = [
        c
        for c in old_external
        if c.source != "sec_edgar" and c.doc_type != "profile" and c.source != "seed"
    ]

    merged: list[EvidenceChunk] = []
    merged.extend(episodic)
    merged.extend(fresh_profile)
    if fresh_sec:
        merged.extend(fresh_sec)
    elif old_sec:
        merged.extend(old_sec)
    else:
        merged.extend(fresh_seed)
    merged.extend(fresh_other if fresh_other else old_other)

    return _dedupe_chunks(merged)
