"""上下文条目统一抽象。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SourceType = Literal[
    "user",
    "tool",
    "document",
    "episodic_memory",
    "semantic_memory",
    "workflow_state",
]


@dataclass
class ContextItem:
    """单条可打包进模型上下文的结构化片段。"""

    content: str
    source_type: SourceType
    source_id: str
    relevance: float = 0.5
    trust_score: float = 0.8
    token_count: int = 0
    priority: int = 50
    key: str = ""

    def __post_init__(self) -> None:
        if not self.key:
            self.key = f"{self.source_type}:{self.source_id}"
