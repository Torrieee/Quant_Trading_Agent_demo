"""Thin OpenAI client helper for optional --live harness paths."""

from __future__ import annotations

import os
from typing import Any

DEFAULT_LIVE_MODEL = "gpt-4o-mini"


def get_openai_client() -> Any | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI(api_key=api_key)


def chat_json_completion(
    client: Any,
    *,
    model: str,
    system: str,
    user: str,
) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("empty_llm_response")
    return content
