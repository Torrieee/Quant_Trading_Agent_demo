"""评测汇总 scorecard。"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .taxonomy import classify_failures


def build_scorecard(
    evalset_id: str,
    results: list[dict[str, Any]],
    *,
    mode: str = "offline",
) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    tag_counter: Counter[str] = Counter()
    bucket_counter: Counter[str] = Counter()
    bucket_pass: Counter[str] = Counter()

    for r in results:
        tags = r.get("failure_tags") or []
        for t in tags:
            tag_counter[t] += 1
        for bucket in r.get("tags") or ["untagged"]:
            bucket_counter[bucket] += 1
            if r.get("passed"):
                bucket_pass[bucket] += 1

    by_bucket: dict[str, dict[str, Any]] = {}
    for bucket, count in bucket_counter.items():
        ok = bucket_pass.get(bucket, 0)
        by_bucket[bucket] = {
            "total": count,
            "passed": ok,
            "pass_rate": round(ok / count, 4) if count else 0.0,
        }

    step_counts = [r.get("step_count", 0) for r in results]
    mean_steps = round(sum(step_counts) / len(step_counts), 2) if step_counts else 0.0

    return {
        "evalset_id": evalset_id,
        "mode": mode,
        "case_count": total,
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "mean_steps": mean_steps,
        },
        "by_bucket": by_bucket,
        "failure_tags": dict(tag_counter),
        "cases": [
            {
                "name": r.get("case_id"),
                "passed": r.get("passed"),
                "tags": r.get("tags"),
                "failure_tags": r.get("failure_tags"),
                "failures": r.get("failures"),
                "step_count": r.get("step_count"),
            }
            for r in results
        ],
    }


def merge_case_result(
    base: dict[str, Any],
    *,
    expect_grade: dict[str, Any],
    tags: list[str] | None = None,
) -> dict[str, Any]:
    failures = list(base.get("failures") or [])
    failures.extend(expect_grade.get("failures") or [])
    passed = len(failures) == 0
    merged = dict(base)
    merged["passed"] = passed
    merged["failures"] = failures
    merged["tags"] = tags or []
    merged["failure_tags"] = classify_failures(failures) if failures else []
    merged["evaluations"] = {
        **(base.get("evaluations") or {}),
        "expectations": expect_grade,
    }
    return merged
