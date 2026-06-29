"""可观测性：trace 导出与可选 Langfuse 上报。"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def trace_dir() -> Path:
    return Path(os.environ.get("AGENT_TRACE_DIR", "data_cache/traces"))


def export_trace(
    *,
    case_id: str,
    symbol: str,
    trace_steps: list[dict[str, Any]],
    final_state: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """写入 JSON trace 文件。"""
    trace_dir().mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = trace_dir() / f"{case_id}_{symbol}_{ts}.json"
    payload = {
        "case_id": case_id,
        "symbol": symbol,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "trace_steps": trace_steps,
        "final_state": final_state or {},
        "extra": extra or {},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _maybe_langfuse(payload)
    return path


def _maybe_langfuse(payload: dict[str, Any]) -> None:
    """若配置 LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY 则 best-effort 上报。"""
    pub = os.environ.get("LANGFUSE_PUBLIC_KEY")
    sec = os.environ.get("LANGFUSE_SECRET_KEY")
    if not pub or not sec:
        return
    try:
        from langfuse import Langfuse

        lf = Langfuse(public_key=pub, secret_key=sec)
        lf.trace(
            name=payload.get("case_id", "analyze"),
            metadata={"symbol": payload.get("symbol")},
            output={"steps": len(payload.get("trace_steps") or [])},
        )
    except Exception:
        pass


def stream_events_from_graph(app, state: dict[str, Any], config: dict[str, Any] | None) -> Iterator[dict[str, Any]]:
    """LangGraph stream 事件标准化。"""
    kwargs: dict[str, Any] = {"stream_mode": "updates"}
    if config:
        for chunk in app.stream(state, config=config, **kwargs):
            yield {"type": "graph_update", "payload": chunk}
    else:
        for chunk in app.stream(state, **kwargs):
            yield {"type": "graph_update", "payload": chunk}
