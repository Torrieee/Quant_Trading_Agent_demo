"""Evidence / Episodic Memory 磁盘持久化。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import EvidenceChunk


def store_dir() -> Path:
    path = Path(os.environ.get("EVIDENCE_STORE_DIR", "data_cache/evidence"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _symbol_path(symbol: str) -> Path:
    safe = symbol.upper().replace("/", "_")
    return store_dir() / f"{safe}.json"


def chunk_from_dict(data: dict[str, Any]) -> EvidenceChunk:
    return EvidenceChunk(
        doc_id=str(data.get("doc_id", "")),
        text=str(data.get("text", "")),
        symbol=str(data.get("symbol", "")).upper(),
        doc_type=str(data.get("doc_type", "")),
        source=str(data.get("source", "")),
        title=str(data.get("title", "")),
        published_at=data.get("published_at"),
        source_url=data.get("source_url"),
        section=data.get("section"),
        score=data.get("score"),
    )


def load_symbol_chunks(symbol: str) -> tuple[list[EvidenceChunk], str | None]:
    """从磁盘加载 symbol 索引；不存在则返回空列表。"""
    path = _symbol_path(symbol)
    if not path.is_file():
        return [], None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], None
    chunks = [chunk_from_dict(c) for c in payload.get("chunks") or [] if isinstance(c, dict)]
    return chunks, payload.get("updated_at")


def save_symbol_chunks(
    symbol: str,
    chunks: list[EvidenceChunk],
    *,
    updated_at: str,
) -> None:
    """持久化 symbol 全量 chunk 列表。"""
    path = _symbol_path(symbol)
    payload = {
        "symbol": symbol.upper(),
        "updated_at": updated_at,
        "chunks": [c.to_dict() for c in chunks],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
