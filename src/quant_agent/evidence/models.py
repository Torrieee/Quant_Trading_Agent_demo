"""Evidence 层数据模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvidenceChunk:
    """单条可检索证据片段。"""

    doc_id: str
    text: str
    symbol: str
    doc_type: str
    source: str
    title: str = ""
    published_at: str | None = None
    source_url: str | None = None
    section: str | None = None
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SymbolIndex:
    """某标的在内存中的索引条目。"""

    symbol: str
    chunks: list[EvidenceChunk] = field(default_factory=list)
    updated_at: str | None = None
