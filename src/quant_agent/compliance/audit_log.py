"""合规：决策审计日志（append-only JSONL）。"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def audit_log_path() -> Path:
    raw = os.environ.get("AUDIT_LOG_PATH", "data_cache/audit/decisions.jsonl")
    return Path(raw)


def append_audit_record(record: dict[str, Any]) -> None:
    """追加一条不可变审计记录。"""
    path = audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **record,
        "audited_at": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
