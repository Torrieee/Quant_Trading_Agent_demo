"""Semantic Memory：从 episodic / 披露中提炼的可检索事实。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .document_rules import RISK_PATTERNS
from .models import EvidenceChunk

MAX_FACTS_PER_SYMBOL = int(os.environ.get("EVIDENCE_MAX_SEMANTIC_FACTS", "50"))


def _store_path(symbol: str) -> Path:
    base = Path(os.environ.get("EVIDENCE_STORE_DIR", "data_cache/evidence"))
    return base / f"{symbol.upper()}_semantic.json"


def load_semantic_facts(symbol: str) -> list[dict[str, Any]]:
    path = _store_path(symbol)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("facts") or [])
    except (json.JSONDecodeError, OSError):
        return []


def save_semantic_facts(symbol: str, facts: list[dict[str, Any]]) -> None:
    path = _store_path(symbol)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"symbol": symbol.upper(), "facts": facts[:MAX_FACTS_PER_SYMBOL]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def facts_to_chunks(symbol: str, facts: list[dict[str, Any]]) -> list[EvidenceChunk]:
    sym = symbol.upper()
    out: list[EvidenceChunk] = []
    for i, f in enumerate(facts):
        text = str(f.get("text", ""))
        if not text:
            continue
        out.append(
            EvidenceChunk(
                doc_id=f.get("fact_id") or f"{sym}_semantic_{i}",
                text=text,
                symbol=sym,
                doc_type="semantic_fact",
                source="semantic_memory",
                title=str(f.get("title", "Semantic fact")),
                published_at=f.get("created_at"),
                section="semantic",
            )
        )
    return out


def extract_facts_from_text(
    symbol: str,
    text: str,
    *,
    source: str,
    case_id: str | None = None,
) -> list[dict[str, Any]]:
    """规则抽取风险/关键事实（无需 LLM）。"""
    sym = symbol.upper()
    lower = text.lower()
    facts: list[dict[str, Any]] = []
    for flag, patterns in RISK_PATTERNS.items():
        for p in patterns:
            if p.lower() not in lower:
                continue
            idx = lower.find(p.lower())
            snippet = text[max(0, idx - 80) : idx + 120].strip()
            facts.append(
                {
                    "fact_id": f"{sym}_fact_{flag}_{len(facts)}",
                    "title": f"{sym} {flag} fact",
                    "text": f"Semantic fact ({flag}): {snippet}",
                    "category": flag,
                    "source": source,
                    "case_id": case_id,
                }
            )
            break
    return facts


def merge_facts(
    existing: list[dict[str, Any]],
    new_facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for f in existing + new_facts:
        fid = str(f.get("fact_id", ""))
        if fid in seen:
            continue
        seen.add(fid)
        merged.append(f)
    return merged[:MAX_FACTS_PER_SYMBOL]


def ingest_semantic_from_session(
    symbol: str,
    *,
    report: str | None,
    decision: dict[str, Any],
    case_id: str,
) -> list[dict[str, Any]]:
    """分析结束后增量写入 semantic facts。"""
    pieces = [report or "", str(decision.get("reasoning", ""))]
    new_facts: list[dict[str, Any]] = []
    for text in pieces:
        new_facts.extend(
            extract_facts_from_text(symbol, text, source="analysis_session", case_id=case_id)
        )
    existing = load_semantic_facts(symbol)
    merged = merge_facts(existing, new_facts)
    save_semantic_facts(symbol, merged)
    return merged
