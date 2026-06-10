"""Optional LLM-as-Judge for local pilot analysis (--live only, not CI)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError

from ..llm_client import DEFAULT_LIVE_MODEL, chat_json_completion

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
        model: str = DEFAULT_LIVE_MODEL,
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
        if self.client is None and self._completion_fn is None:
            return {
                "judge_mode": "rule_only_fallback",
                "judge_error": "no_openai_client",
                **base_meta,
            }
        try:
            raw = self._call_judge(case, trace, rule_evaluations or {})
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

    def _call_judge(
        self,
        case: dict[str, Any],
        trace: dict[str, Any],
        rule_evaluations: dict[str, Any],
    ) -> str:
        system = (
            "You are an evaluator for multi-tool agent traces. "
            "Return JSON with keys: scores (tool_selection, evidence_sufficiency, "
            "efficiency, answer_grounding as integers 1-5) and comments (string)."
        )
        user = json.dumps(
            {
                "task": case.get("name"),
                "gate": case.get("gate", {}),
                "trace": trace,
                "rule_evaluations": rule_evaluations,
            },
            ensure_ascii=False,
            default=str,
        )
        if self._completion_fn is not None:
            return self._completion_fn(system=system, user=user)
        return chat_json_completion(
            self.client,
            model=self.model,
            system=system,
            user=user,
        )
