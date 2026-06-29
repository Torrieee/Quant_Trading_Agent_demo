"""可靠性评测：pass@k、pass^k 与故障注入。"""

from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any

import yaml

from ..runtime.tool_adapter import HarnessToolAdapter
from ..runtime.tool_policy import ToolExecutionPolicy
from ..runtime.runner import RuntimeRunner
from .fake_model import resolve_fake_model
from .graders import evaluate_expectations
from .runner import _apply_setup, _build_case_payload, isolated_eval_env

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RELIABILITY_EVALSET = PROJECT_ROOT / "evalsets" / "reliability_v1.yaml"


def load_reliability_evalset(path: Path | str) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"reliability evalset 格式错误: {path}")
    return data


def pass_at_k(successes: list[bool], k: int) -> float:
    """至少一次成功概率（此处用经验频率）。"""
    if not successes:
        return 0.0
    return 1.0 if any(successes[:k]) else 0.0


def pass_pow_k(successes: list[bool], k: int) -> float:
    """连续 k 次全部成功。"""
    if len(successes) < k:
        return 0.0
    window = successes[:k]
    return 1.0 if all(window) else 0.0


def _run_case_once(
    payload: dict[str, Any],
    *,
    use_fake: bool,
    fault: dict[str, Any] | None,
) -> dict[str, Any]:
    name = payload["name"]
    expect = payload.get("expect") or {}
    setup = payload.get("setup") or {}
    symbol = payload.get("symbol", "FIXTURE")

    if setup:
        _apply_setup(setup, symbol)

    policy = ToolExecutionPolicy(max_retries=int(payload.get("max_tool_retries", 2)))
    adapter = HarnessToolAdapter(policy=policy)
    if fault:
        adapter.set_fault_injection(fault)

    model = resolve_fake_model(payload.get("fake_model")) if use_fake else None
    runner = RuntimeRunner(adapter=adapter, model=model)
    raw = runner.run_case(payload, write_trace=False)
    expect_grade = evaluate_expectations(raw, expect)
    passed = raw.get("passed", False) and expect_grade["passed"]
    failures = list(raw.get("failures") or []) + list(expect_grade.get("failures") or [])
    return {
        "case_id": name,
        "passed": passed,
        "failures": failures,
        "retry_observed": _extract_max_retry(raw),
        "raw": raw,
    }


def _extract_max_retry(raw: dict[str, Any]) -> int:
    max_r = 0
    for step in (raw.get("trace") or {}).get("steps") or []:
        obs = step.get("observation") or {}
        if isinstance(obs, dict):
            max_r = max(max_r, int(obs.get("retry_count") or 0))
    return max_r


def run_reliability_eval(path: Path | str | None = None) -> dict[str, Any]:
    spec = load_reliability_evalset(path or DEFAULT_RELIABILITY_EVALSET)
    defaults = spec.get("defaults") or {}
    cases = spec.get("cases") or []
    use_fake = (spec.get("model") or "fake").lower() != "live"
    k = int(spec.get("repeat_k", 3))

    results: list[dict[str, Any]] = []
    with isolated_eval_env():
        for case in cases:
            payload = _build_case_payload(case, defaults)
            repeats = int(payload.get("repeat", k))
            fault = payload.get("fault_injection")
            run_results: list[dict[str, Any]] = []
            for i in range(repeats):
                run_results.append(
                    _run_case_once(payload, use_fake=use_fake, fault=fault)
                )

            successes = [r["passed"] for r in run_results]
            entry = {
                "name": payload["name"],
                "tags": list(payload.get("tags") or []),
                "repeat": repeats,
                "pass_at_1": pass_at_k(successes, 1),
                f"pass^{repeats}": pass_pow_k(successes, repeats),
                "success_rate": round(sum(successes) / max(len(successes), 1), 3),
                "runs": [
                    {"run": i + 1, "passed": r["passed"], "retry_observed": r["retry_observed"]}
                    for i, r in enumerate(run_results)
                ],
                "passed": all(successes),
                "failures": [f for r in run_results for f in r["failures"]],
            }
            if fault:
                entry["fault_injection"] = fault
                entry["retry_required"] = fault.get("fail_count", 1)
                entry["retry_observed_max"] = max(r["retry_observed"] for r in run_results)
            results.append(entry)

    passed_cases = sum(1 for r in results if r["passed"])
    total = len(results)
    min_pass_pow = float((spec.get("benchmark") or {}).get("min_pass_pow_k", 0.0))
    min_pass_rate = float((spec.get("benchmark") or {}).get("min_pass_rate", 0.0))
    eval_focus = spec.get("eval_focus") or (
        "fault_recovery" if use_fake else "live_policy_stability"
    )

    aggregate_pass_pow = (
        statistics.mean([r.get(f"pass^{r['repeat']}", 0.0) for r in results if r["repeat"] > 1])
        if any(r["repeat"] > 1 for r in results)
        else 1.0
    )
    case_pass_rate = passed_cases / total if total else 0.0

    if min_pass_rate > 0:
        bench_passed = case_pass_rate >= min_pass_rate
        bench_detail = {
            "min_pass_rate": min_pass_rate,
            "actual_pass_rate": round(case_pass_rate, 3),
        }
    elif min_pass_pow > 0:
        bench_passed = aggregate_pass_pow >= min_pass_pow and passed_cases == total
        bench_detail = {
            "min_pass_pow_k": min_pass_pow,
            "actual_mean_pass_pow_k": round(aggregate_pass_pow, 3),
        }
    else:
        bench_passed = passed_cases == total
        bench_detail = {}

    return {
        "evalset_id": spec.get("evalset_id", "reliability_v1"),
        "mode": "offline" if use_fake else "live",
        "eval_focus": eval_focus,
        "repeat_k": k,
        "results": results,
        "summary": {
            "passed_cases": passed_cases,
            "total_cases": total,
            "case_pass_rate": round(case_pass_rate, 3),
            "mean_pass_pow_k": round(aggregate_pass_pow, 3),
        },
        "benchmark": {
            "passed": bench_passed,
            **bench_detail,
        },
    }
