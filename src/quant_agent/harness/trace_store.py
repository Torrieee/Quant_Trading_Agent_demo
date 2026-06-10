"""Persist and query agent traces on disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .trace import AgentTrace


class TraceStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, trace: AgentTrace | dict[str, Any]) -> Path:
        data = trace.to_dict() if isinstance(trace, AgentTrace) else trace
        case_id = data.get("case_id", "unknown")
        attempt = data.get("attempt", 1)
        name = f"{case_id}_attempt{attempt}.json"
        path = self.root / name
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return path

    def list_traces(self) -> list[Path]:
        return sorted(self.root.glob("*.json"))

    def load(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def filter(
        self,
        *,
        error_type: str | None = None,
        case_id: str | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for path in self.list_traces():
            data = self.load(path)
            if case_id and data.get("case_id") != case_id:
                continue
            if error_type:
                steps = data.get("steps") or []
                if not any(s.get("error_type") == error_type for s in steps):
                    continue
            results.append(data)
        return results
