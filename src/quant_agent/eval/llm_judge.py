"""Optional LLM-as-Judge for live capability eval."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError

PROMPT_VERSION = "judge_v1"


class JudgeScores(BaseModel):
    tool_selection: int = Field(ge=1, le=5)
    evidence_sufficiency: int = Field(ge=1, le=5)
    efficiency: int = Field(ge=1, le=5)
    answer_grounding: int = Field(ge=1, le=5)


class JudgeResponse(BaseModel):
    scores: JudgeScores
    comments: str = ""


class LLMJudge:
    def __init__(
        self,
        client: Any | None,
        *,
        model: str = "deepseek-chat",
        completion_fn: Callable[..., str] | None = None,
    ) -> None:
        self.client = client
        self.model = model
        self._completion_fn = completion_fn

    def evaluate(
        self,
        case: dict[str, Any],
        trace: dict[str, Any],
        *,
        rule_evaluations: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        base_meta = {
            "model": self.model,
            "prompt_version": PROMPT_VERSION,
            "timestamp": timestamp,
        }
        if self._completion_fn is None:
            return {
                "judge_mode": "rule_only_fallback",
                "judge_error": "no_completion_fn",
                **base_meta,
            }
        try:
            raw = self._completion_fn(
                system=self._system_prompt(),
                user=self._user_payload(case, trace, rule_evaluations or {}),
            )
            payload = json.loads(raw)
            parsed = JudgeResponse.model_validate(payload)
            return {
                "judge_mode": "live",
                "scores": parsed.scores.model_dump(),
                "comments": parsed.comments,
                **base_meta,
            }
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
            return {
                "judge_mode": "rule_only_fallback",
                "judge_error": f"schema_validation_failed: {exc}",
                **base_meta,
            }
        except Exception as exc:
            return {
                "judge_mode": "rule_only_fallback",
                "judge_error": str(exc),
                **base_meta,
            }

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are an evaluator for multi-tool agent traces. "
            "Return JSON with keys: scores (tool_selection, evidence_sufficiency, "
            "efficiency, answer_grounding as integers 1-5) and comments (string)."
        )

    @staticmethod
    def _user_payload(
        case: dict[str, Any],
        trace: dict[str, Any],
        rule_evaluations: dict[str, Any],
    ) -> str:
        return json.dumps(
            {
                "task": case.get("name"),
                "gate": case.get("gate", {}),
                "trace": trace,
                "rule_evaluations": rule_evaluations,
            },
            ensure_ascii=False,
            default=str,
        )
