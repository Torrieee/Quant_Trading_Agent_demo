"""Live 评测：DeepSeek LLM-as-Judge。"""

from __future__ import annotations

import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from ..agents.llm import require_deepseek_chat_model
from .llm_judge import LLMJudge


def run_live_judge(
    case: dict[str, Any],
    trace: dict[str, Any],
    *,
    rule_evaluations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """使用 DeepSeek 对单条 case trace 打分。"""
    model_name = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    def completion_fn(*, system: str, user: str) -> str:
        chat = require_deepseek_chat_model(temperature=0.0)
        response = chat.invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        content = getattr(response, "content", None) or str(response)
        if not content:
            raise ValueError("empty_judge_response")
        return content

    judge = LLMJudge(
        client=None,
        model=model_name,
        completion_fn=completion_fn,
    )
    return judge.evaluate(
        case,
        trace,
        rule_evaluations=rule_evaluations or {},
    )


def grade_judge_scores(
    judge_result: dict[str, Any],
    *,
    min_score: int = 3,
    require_judge: bool = False,
) -> dict[str, Any]:
    """将 judge 分数转为 pass/fail 断言。"""
    failures: list[str] = []
    scores = judge_result.get("scores")
    mode = judge_result.get("judge_mode", "")

    if not scores:
        if require_judge:
            err = judge_result.get("judge_error", "no_scores")
            failures.append(f"judge: 未获得分数 ({err})")
        return {"passed": len(failures) == 0, "failures": failures, "scores": scores}

    for dim, value in scores.items():
        try:
            score = int(value)
        except (TypeError, ValueError):
            failures.append(f"judge: {dim} 分数无效 ({value})")
            continue
        if score < min_score:
            failures.append(f"judge: {dim}={score} < 最低 {min_score}")

    if require_judge and mode != "live":
        failures.append(f"judge: 期望 live 模式，实际 {mode}")

    return {"passed": len(failures) == 0, "failures": failures, "scores": scores}
