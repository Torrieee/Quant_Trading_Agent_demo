"""Token 预算估算与配置。"""

from __future__ import annotations

import os


def estimate_tokens(text: str) -> int:
    """粗估 token 数（中英混合约 4 字符 / token）。"""
    if not text:
        return 0
    return max(1, len(text) // 4)


def default_context_budget() -> int:
    """模型上下文 token 预算（可通过 AGENT_CONTEXT_BUDGET 覆盖）。"""
    try:
        return int(os.environ.get("AGENT_CONTEXT_BUDGET", "8000"))
    except ValueError:
        return 8000
