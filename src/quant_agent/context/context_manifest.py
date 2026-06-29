"""Context 打包清单（可观测 / 评测）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextManifest:
    context_budget: int
    used_tokens: int = 0
    dropped_items: int = 0
    compressed_items: int = 0
    kept_items: int = 0
    source_distribution: dict[str, float] = field(default_factory=dict)
    dropped_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_budget": self.context_budget,
            "used_tokens": self.used_tokens,
            "dropped_items": self.dropped_items,
            "compressed_items": self.compressed_items,
            "kept_items": self.kept_items,
            "source_distribution": dict(self.source_distribution),
            "dropped_keys": list(self.dropped_keys),
        }
