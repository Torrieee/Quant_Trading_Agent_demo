"""LLM-as-Judge fallback tests (no live API required)."""

from __future__ import annotations

import json

from quant_agent.harness.evaluators.llm_judge import LLMJudge
from quant_agent.harness.planner import LLMPlanner, OfflinePlanner
from quant_agent.llm_agent import TradingFunctionCaller


def test_judge_invalid_json_falls_back_to_rule_only():
    def bad_completion(**_kwargs):
        return "not-json"

    judge = LLMJudge(client=object(), completion_fn=bad_completion)
    result = judge.evaluate(
        {"name": "demo", "gate": {}},
        {"case_id": "demo", "steps": []},
    )
    assert result["judge_mode"] == "rule_only_fallback"
    assert "schema_validation_failed" in result["judge_error"]
    assert result["prompt_version"] == "judge_v1"
    assert result["model"]


def test_judge_missing_scores_falls_back():
    def incomplete(**_kwargs):
        return json.dumps({"comments": "ok"})

    judge = LLMJudge(client=object(), completion_fn=incomplete)
    result = judge.evaluate({"name": "demo"}, {"steps": []})
    assert result["judge_mode"] == "rule_only_fallback"


def test_judge_valid_response_parsed():
    def good(**_kwargs):
        return json.dumps(
            {
                "scores": {
                    "tool_selection": 4,
                    "evidence_sufficiency": 3,
                    "efficiency": 5,
                    "answer_grounding": 4,
                },
                "comments": "looks grounded",
            }
        )

    judge = LLMJudge(client=object(), completion_fn=good)
    result = judge.evaluate({"name": "demo"}, {"steps": []})
    assert result["judge_mode"] == "live"
    assert result["scores"]["tool_selection"] == 4
    assert result["comments"] == "looks grounded"


def test_judge_no_client_falls_back():
    judge = LLMJudge(client=None)
    result = judge.evaluate({"name": "demo"}, {"steps": []})
    assert result["judge_mode"] == "rule_only_fallback"
    assert result["judge_error"] == "no_openai_client"


def test_llm_planner_falls_back_to_offline_plan():
    case = {
        "name": "fallback_case",
        "plan": [
            {
                "tool": "get_strategy_recommendation",
                "arguments": {"market_state": "ranging"},
            }
        ],
    }

    def bad_plan(**_kwargs):
        return json.dumps({"plan": [{"tool": "unknown_tool", "arguments": {}}]})

    planner = LLMPlanner(
        TradingFunctionCaller(),
        client=object(),
        fallback=OfflinePlanner(),
        completion_fn=bad_plan,
    )
    plan = planner.build_plan(case)
    assert plan[0]["tool"] == "get_strategy_recommendation"
