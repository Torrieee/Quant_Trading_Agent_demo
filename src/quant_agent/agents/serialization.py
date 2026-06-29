"""LangGraph checkpoint 可序列化的 analysis_data 编解码。"""

from __future__ import annotations

from io import StringIO
from typing import Any

import numpy as np
import pandas as pd

_DF_MARKER = "__pandas_dataframe__"


def serialize_analysis_data(data: dict[str, Any] | None) -> dict[str, Any]:
    """将 analysis_data 转为 checkpoint 可持久化结构。"""
    if not data:
        return {}
    out = dict(data)
    hist = out.get("historical_data")
    if isinstance(hist, pd.DataFrame):
        out["historical_data"] = {
            _DF_MARKER: True,
            "payload": hist.to_json(orient="split", date_format="iso"),
        }
    return out


def hydrate_analysis_data(data: dict[str, Any] | None) -> dict[str, Any]:
    """从 checkpoint 状态还原 analysis_data（含 DataFrame）。"""
    if not data:
        return {}
    out = dict(data)
    hist = out.get("historical_data")
    if isinstance(hist, dict) and hist.get(_DF_MARKER):
        payload = hist.get("payload")
        if isinstance(payload, str) and payload:
            out["historical_data"] = pd.read_json(StringIO(payload), orient="split")
        else:
            out.pop("historical_data", None)
    return out


def resolve_analysis_data(state: dict[str, Any]) -> dict[str, Any]:
    """节点读取 analysis_data 时统一 hydrate。"""
    return hydrate_analysis_data(state.get("analysis_data"))


def sanitize_for_checkpoint(obj: Any) -> Any:
    """将 numpy / pandas 转为 checkpoint 可序列化类型。"""
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.DataFrame):
        return serialize_analysis_data({"historical_data": obj})["historical_data"]
    if isinstance(obj, pd.Series):
        return obj.astype(object).where(pd.notna(obj), None).tolist()
    if isinstance(obj, dict):
        return {str(k): sanitize_for_checkpoint(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_checkpoint(v) for v in obj]
    return obj
