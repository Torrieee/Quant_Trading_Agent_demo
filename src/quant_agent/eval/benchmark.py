"""评测 benchmark 门槛校验。"""

from __future__ import annotations

from typing import Any


def check_benchmark(
    scorecard: dict[str, Any],
    benchmark: dict[str, Any] | None,
    *,
    judge_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """对照 evalset benchmark 块检查是否达标。"""
    benchmark = benchmark or {}
    failures: list[str] = []

    min_pass_rate = float(benchmark.get("min_pass_rate", 1.0))
    actual_rate = float(scorecard.get("summary", {}).get("pass_rate", 0.0))
    if actual_rate < min_pass_rate:
        failures.append(
            f"benchmark: pass_rate {actual_rate:.0%} < 最低 {min_pass_rate:.0%}"
        )

    if benchmark.get("require_judge") and judge_summary:
        avg = judge_summary.get("mean_overall")
        min_judge = float(benchmark.get("judge_min_score", 3))
        if avg is not None and avg < min_judge:
            failures.append(
                f"benchmark: judge 均值 {avg:.2f} < 最低 {min_judge}"
            )

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "thresholds": {
            "min_pass_rate": min_pass_rate,
            "judge_min_score": benchmark.get("judge_min_score"),
            "require_judge": benchmark.get("require_judge", False),
        },
        "actual": {
            "pass_rate": actual_rate,
            "judge_mean": (judge_summary or {}).get("mean_overall"),
        },
    }


def summarize_judge_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总各 case 的 LLM judge 分数。"""
    dims = ["tool_selection", "evidence_sufficiency", "efficiency", "answer_grounding"]
    totals = {d: 0.0 for d in dims}
    counts = {d: 0 for d in dims}
    judged_cases = 0

    for result in results:
        judge = (result.get("evaluations") or {}).get("llm_judge") or {}
        scores = judge.get("scores")
        if not scores:
            continue
        judged_cases += 1
        for dim in dims:
            if dim in scores:
                totals[dim] += float(scores[dim])
                counts[dim] += 1

    means = {
        dim: round(totals[dim] / counts[dim], 2) if counts[dim] else None
        for dim in dims
    }
    valid = [v for v in means.values() if v is not None]
    mean_overall = round(sum(valid) / len(valid), 2) if valid else None

    return {
        "judged_cases": judged_cases,
        "dimension_means": means,
        "mean_overall": mean_overall,
    }
