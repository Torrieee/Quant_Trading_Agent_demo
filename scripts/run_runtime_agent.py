"""Run LangGraph multi-agent runtime (DeepSeek API only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from quant_agent.agents.llm import DeepSeekConfigError, require_deepseek_chat_model
from quant_agent.runtime.runner import RuntimeRunner, run_runtime_task


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LangGraph Supervisor + Research/Risk/Reporter (DeepSeek API)"
    )
    parser.add_argument(
        "--task",
        type=str,
        default="Recommend a strategy for ranging market and size the position",
        help="Natural language task",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=None,
        help="YAML file of runtime cases (e.g. harness/cases/runtime_cases.yaml)",
    )
    parser.add_argument(
        "--case-name",
        type=str,
        default=None,
        help="Run only one case by name from --cases file",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write JSON result to path",
    )
    args = parser.parse_args()

    try:
        require_deepseek_chat_model()
    except DeepSeekConfigError as exc:
        print(exc, file=sys.stderr)
        sys.exit(2)

    runner = RuntimeRunner()
    results: list[dict] = []

    if args.cases:
        cases = yaml.safe_load(args.cases.read_text(encoding="utf-8")) or []
        if args.case_name:
            cases = [c for c in cases if c.get("name") == args.case_name]
        for case in cases:
            results.append(runner.run_case(case, write_trace=True))
    else:
        results.append(run_runtime_task(args.task))

    for result in results:
        _print_result(result)

    if args.report and len(results) == 1:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(results[0], indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )


def _print_result(result: dict) -> None:
    print(f"\nCase: {result.get('case_id')} | passed={result.get('passed')}")
    print(f"Agents: {result.get('agents_visited')}")
    print(f"Risk: {result.get('risk_verdict')}")
    if result.get("report"):
        print("\n--- Report ---")
        print(result["report"][:2000])
    if result.get("failures"):
        print("\nFailures:", result["failures"])


if __name__ == "__main__":
    main()
