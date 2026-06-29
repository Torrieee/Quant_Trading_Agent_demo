"""将 workflow quant_state 打包为带预算的结构化上下文。"""

from __future__ import annotations

import json
from typing import Any

from .context_item import ContextItem
from .context_manifest import ContextManifest
from .token_budget import default_context_budget, estimate_tokens

# 各来源在预算中的最低配额比例
_SOURCE_QUOTAS: dict[str, float] = {
    "workflow_state": 0.15,
    "document": 0.35,
    "episodic_memory": 0.15,
    "semantic_memory": 0.10,
    "tool": 0.15,
    "user": 0.10,
}

# quant_state 键 → (source_type, priority, max_chars)
_STATE_KEY_META: dict[str, tuple[str, int, int]] = {
    "preliminary_decision": ("workflow_state", 90, 1200),
    "recommended_strategy": ("workflow_state", 85, 200),
    "market_regime": ("workflow_state", 80, 200),
    "individual_signals": ("workflow_state", 70, 2000),
    "document_signal": ("workflow_state", 88, 800),
    "risk_flags": ("workflow_state", 82, 400),
    "evidence_snapshot": ("document", 75, 4000),
    "episodic_memory": ("episodic_memory", 72, 3000),
    "semantic_facts": ("semantic_memory", 68, 2000),
    "research_findings": ("workflow_state", 74, 2500),
    "research_summary": ("workflow_state", 73, 1500),
    "position_size": ("tool", 60, 200),
}


def _truncate(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[: max_chars - 20] + "\n...[truncated]", True


def _items_from_quant_state(quant_state: dict[str, Any]) -> list[ContextItem]:
    items: list[ContextItem] = []
    for key, value in quant_state.items():
        if key in ("context_manifest",):
            continue
        if value is None or value == "" or value == {} or value == []:
            continue

        meta = _STATE_KEY_META.get(key)
        if meta:
            source_type, priority, max_chars = meta
        else:
            source_type, priority, max_chars = "tool", 40, 1500

        if isinstance(value, (dict, list)):
            raw = json.dumps(value, ensure_ascii=False, default=str)
        else:
            raw = str(value)

        content, compressed = _truncate(raw, max_chars)
        tokens = estimate_tokens(content)
        items.append(
            ContextItem(
                content=content,
                source_type=source_type,  # type: ignore[arg-type]
                source_id=key,
                relevance=min(1.0, priority / 100.0),
                trust_score=0.85 if source_type == "workflow_state" else 0.75,
                token_count=tokens,
                priority=priority,
                key=f"{source_type}:{key}",
            )
        )
        if compressed:
            items[-1].token_count = estimate_tokens(content)

    return items


def _dedupe_items(items: list[ContextItem]) -> list[ContextItem]:
    seen: set[str] = set()
    out: list[ContextItem] = []
    for item in sorted(items, key=lambda x: (-x.priority, -x.relevance)):
        fingerprint = item.content[:120]
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        out.append(item)
    return out


def _apply_budget(items: list[ContextItem], budget: int) -> tuple[list[ContextItem], ContextManifest]:
    manifest = ContextManifest(context_budget=budget)
    if not items:
        return [], manifest

    by_source: dict[str, list[ContextItem]] = {}
    for item in items:
        by_source.setdefault(item.source_type, []).append(item)

    kept: list[ContextItem] = []
    used = 0

    # 按配额分阶段纳入
    for source_type, quota_frac in _SOURCE_QUOTAS.items():
        source_budget = int(budget * quota_frac)
        source_used = 0
        for item in sorted(by_source.get(source_type, []), key=lambda x: -x.priority):
            if source_used + item.token_count > source_budget:
                manifest.dropped_items += 1
                manifest.dropped_keys.append(item.key)
                continue
            if used + item.token_count > budget:
                manifest.dropped_items += 1
                manifest.dropped_keys.append(item.key)
                continue
            kept.append(item)
            source_used += item.token_count
            used += item.token_count

    # 剩余高优先级项（其他 source_type）
    for item in sorted(items, key=lambda x: -x.priority):
        if item in kept:
            continue
        if used + item.token_count > budget:
            manifest.dropped_items += 1
            manifest.dropped_keys.append(item.key)
            continue
        kept.append(item)
        used += item.token_count

    manifest.kept_items = len(kept)
    manifest.used_tokens = used
    if used:
        dist: dict[str, int] = {}
        for item in kept:
            dist[item.source_type] = dist.get(item.source_type, 0) + item.token_count
        manifest.source_distribution = {
            k: round(v / used, 3) for k, v in sorted(dist.items())
        }

    return kept, manifest


def pack_workflow_context(
    quant_state: dict[str, Any],
    *,
    task: str = "",
    symbol: str | None = None,
    budget: int | None = None,
) -> tuple[str, ContextManifest]:
    """
    将 quant_state 转为结构化上下文字符串 + manifest。
    返回的文本可直接嵌入 ReAct HumanMessage。
    """
    budget = budget or default_context_budget()
    items = _items_from_quant_state(quant_state)

    if task:
        task_item = ContextItem(
            content=task,
            source_type="user",
            source_id="task",
            relevance=1.0,
            trust_score=1.0,
            token_count=estimate_tokens(task),
            priority=95,
            key="user:task",
        )
        items.insert(0, task_item)

    if symbol:
        sym_item = ContextItem(
            content=f"Symbol: {symbol.upper()}",
            source_type="user",
            source_id="symbol",
            relevance=0.9,
            trust_score=1.0,
            token_count=estimate_tokens(symbol),
            priority=92,
            key="user:symbol",
        )
        items.insert(0, sym_item)

    items = _dedupe_items(items)
    kept, manifest = _apply_budget(items, budget)

    sections: dict[str, list[str]] = {}
    for item in sorted(kept, key=lambda x: -x.priority):
        sections.setdefault(item.source_type, []).append(
            f"### {item.source_id}\n{item.content}"
        )

    lines = ["# Packed Context"]
    for source_type in (
        "user",
        "workflow_state",
        "document",
        "episodic_memory",
        "semantic_memory",
        "tool",
    ):
        if source_type in sections:
            lines.append(f"\n## {source_type}")
            lines.extend(sections[source_type])

    return "\n".join(lines), manifest
