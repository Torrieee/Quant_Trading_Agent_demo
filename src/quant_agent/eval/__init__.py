"""QuantEngine Agent evaluation framework."""

from .benchmark import check_benchmark, summarize_judge_results
from .fake_model import HighPositionFakeModel, RoleAwareFakeModel, resolve_fake_model
from .graders import evaluate_expectations
from .judge import grade_judge_scores, run_live_judge
from .scorecard import build_scorecard, merge_case_result
from .taxonomy import classify_failures

_RUNNER_EXPORTS = {
    "DEFAULT_EVALSET",
    "DEFAULT_LIVE_EVALSET",
    "AgentEvalRunner",
    "load_evalset",
    "write_eval_markdown",
    "write_eval_report",
}

__all__ = [
    "AgentEvalRunner",
    "DEFAULT_EVALSET",
    "DEFAULT_LIVE_EVALSET",
    "RoleAwareFakeModel",
    "HighPositionFakeModel",
    "resolve_fake_model",
    "evaluate_expectations",
    "build_scorecard",
    "merge_case_result",
    "classify_failures",
    "load_evalset",
    "write_eval_report",
    "write_eval_markdown",
    "run_live_judge",
    "grade_judge_scores",
    "check_benchmark",
    "summarize_judge_results",
]


def __getattr__(name: str):
    if name in _RUNNER_EXPORTS:
        from . import runner

        return getattr(runner, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
