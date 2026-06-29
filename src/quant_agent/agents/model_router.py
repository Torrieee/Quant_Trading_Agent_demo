"""按节点角色路由不同 LLM 配置。"""

from __future__ import annotations

import os
from typing import Any

from .llm import get_deepseek_chat_model, require_deepseek_chat_model

_ROLE_ENV = {
    "research": "DEEPSEEK_MODEL_RESEARCH",
    "risk": "DEEPSEEK_MODEL_RISK",
    "reporter": "DEEPSEEK_MODEL_REPORTER",
    "router": "DEEPSEEK_MODEL_ROUTER",
}


def get_model_for_role(role: str, *, fallback: Any | None = None) -> Any:
    """
    为指定角色解析模型；未配置角色专用 env 时回退 DEEPSEEK_MODEL / fallback。
    router 默认更低 temperature。
    """
    env_key = _ROLE_ENV.get(role)
    model_name = os.environ.get(env_key) if env_key else None
    temp = 0.0
    if role == "router":
        temp = float(os.environ.get("DEEPSEEK_ROUTER_TEMPERATURE", "0"))

    if fallback is not None and not model_name and role != "router":
        return fallback

    chat = get_deepseek_chat_model(model=model_name, temperature=temp)
    if chat is not None:
        return chat
    if fallback is not None:
        return fallback
    return require_deepseek_chat_model(model=model_name, temperature=temp)
