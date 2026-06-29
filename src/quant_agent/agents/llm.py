"""DeepSeek 大模型接入（OpenAI 兼容接口）。"""

from __future__ import annotations

import os
from typing import Any

DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekConfigError(RuntimeError):
    """未配置 DeepSeek API 时抛出。"""


def get_deepseek_chat_model(
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> Any | None:
    """返回 LangChain ChatOpenAI 实例；无 API Key 时返回 None。"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        return None

    return ChatOpenAI(
        model=model or os.environ.get("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
        api_key=api_key,
        base_url=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL),
        temperature=temperature,
    )


def require_deepseek_chat_model(
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> Any:
    """获取 DeepSeek 模型，未配置则抛出说明性异常。"""
    chat = get_deepseek_chat_model(model=model, temperature=temperature)
    if chat is None:
        raise DeepSeekConfigError(
            "需要 DeepSeek API。请设置环境变量 DEEPSEEK_API_KEY。"
            "可选：DEEPSEEK_MODEL（默认 deepseek-chat）、"
            "DEEPSEEK_BASE_URL（默认 https://api.deepseek.com）。"
        )
    return chat


def has_deepseek_api_key() -> bool:
    return bool(os.environ.get("DEEPSEEK_API_KEY"))
