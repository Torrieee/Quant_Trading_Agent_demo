"""Run 4 pilot tasks (default offline) and write benchmark report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from quant_agent.harness.pilot_benchmark import (  # noqa: E402
    build_sample_trace_example,
    run_pilot_benchmark,
    write_pilot_markdown,
    write_pilot_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pilot benchmark (4 tasks)")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Optional live mode (MVP still uses offline plans; records mode=live)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "pilot_benchmark.json",
        help="Local benchmark JSON output",
    )
    parser.add_argument(
        "--write-examples",
        action="store_true",
        help="Also write reports/examples/ sample artifacts for the repo",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Write traces to reports/traces/ while running",
    )
    args = parser.parse_args()

    report = run_pilot_benchmark(live=args.live, write_trace=args.trace)
    write_pilot_report(report, args.output)
    md_path = args.output.with_suffix(".md")
    write_pilot_markdown(report, md_path)

    s = report["summary"]
    print(
        f"Pilot ({report['mode']}): {s['passed']}/{report['pilot_task_count']} passed "
        f"(tool_correctness={s['tool_correctness_rate']:.0%}, "
        f"evidence_coverage={s['evidence_coverage_rate']:.0%})"
    )
    print(f"Report: {args.output}")
    print(f"Markdown: {md_path}")

    if args.write_examples:
        examples = PROJECT_ROOT / "reports" / "examples"
        write_pilot_report(
            report,
            examples / "sample_pilot_benchmark.json",
            is_sample=True,
        )
        write_pilot_markdown(report, examples / "sample_eval_report.md")
        sample_trace = build_sample_trace_example()
        import json

        (examples / "sample_trace.json").write_text(
            json.dumps(sample_trace, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"Examples written to {examples}")

    if s["failed"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
