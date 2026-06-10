"""Run Agent Quality Harness from CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from quant_agent.harness.runner import run_harness


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Quality Harness")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/harness_report.json"),
        help="Path to write JSON report",
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help="Exit 1 if any case fails structural quality checks",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Optional LLM Planner/Judge/Reflection (not used in CI)",
    )
    args = parser.parse_args()

    report = run_harness(report_path=args.report, gate=args.gate, live=args.live)
    summary = report["summary"]
    print(
        f"Harness: {summary['passed']}/{summary['total']} passed "
        f"(pass_rate={summary['pass_rate']:.0%})"
    )
    print(f"Report written to {args.report}")


if __name__ == "__main__":
    main()
