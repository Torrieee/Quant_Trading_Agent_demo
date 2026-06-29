"""LangGraph Checkpointer 工厂（Memory / SQLite）。"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

_checkpointer: Any | None = None
_sqlite_conn: sqlite3.Connection | None = None


def is_checkpoint_enabled() -> bool:
    """是否启用 LangGraph checkpoint（默认 sqlite）。"""
    val = os.environ.get("LANGGRAPH_CHECKPOINT", "sqlite").strip().lower()
    return val not in ("0", "false", "none", "off", "disabled")


def checkpoint_backend() -> str:
    return os.environ.get("LANGGRAPH_CHECKPOINT", "sqlite").strip().lower()


def checkpoint_db_path() -> Path:
    raw = os.environ.get("LANGGRAPH_CHECKPOINT_DB", "data_cache/checkpoints/langgraph.db")
    return Path(raw)


def workflow_invoke_config(
    case_id: str,
    *,
    thread_id: str | None = None,
    checkpoint_id: str | None = None,
) -> dict[str, Any]:
    """构建 invoke / get_state 用的 configurable。"""
    cfg: dict[str, Any] = {"thread_id": thread_id or case_id}
    if checkpoint_id:
        cfg["checkpoint_id"] = checkpoint_id
    return {"configurable": cfg}


def get_checkpointer(*, force_new: bool = False):
    """
    获取进程内单例 checkpointer。
    - memory：测试 / 调试
    - sqlite：默认持久化（需 langgraph-checkpoint-sqlite）
    """
    global _checkpointer, _sqlite_conn
    if _checkpointer is not None and not force_new:
        return _checkpointer

    backend = checkpoint_backend()
    if backend in ("0", "false", "none", "off", "disabled"):
        _checkpointer = None
        return None

    if backend == "memory":
        _checkpointer = MemorySaver()
        return _checkpointer

    if backend == "sqlite":
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
        except ImportError:
            _checkpointer = MemorySaver()
            return _checkpointer

        db_path = checkpoint_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if _sqlite_conn is None or force_new:
            _sqlite_conn = sqlite3.connect(str(db_path), check_same_thread=False)
        _checkpointer = SqliteSaver(_sqlite_conn)
        return _checkpointer

    _checkpointer = MemorySaver()
    return _checkpointer


def reset_checkpointer() -> None:
    """测试重置 checkpointer 单例。"""
    global _checkpointer, _sqlite_conn
    _checkpointer = None
    if _sqlite_conn is not None:
        try:
            _sqlite_conn.close()
        except sqlite3.Error:
            pass
    _sqlite_conn = None
