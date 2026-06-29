#!/usr/bin/env python3
"""扫描 data_cache/traces 并生成失败聚类 / taxonomy 归因报告。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from quant_agent.observability.trace_analysis import analyze_traces, write_trace_insights_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze agent traces and cluster failures")
    parser.add_argument(
        "--trace-dir",
        type=Path,
        default=PROJECT_ROOT / "data_cache" / "traces",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "trace_insights.json",
    )
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    report = analyze_traces(args.trace_dir, limit=args.limit)
    path = write_trace_insights_report(report, args.output)

    s = report["summary"]
    print(f"Traces analyzed: {s['trace_count']}")
    print(f"With failures: {s['traces_with_failures']} ({s['failure_rate']:.0%})")
    print("Top tags:")
    for item in s.get("top_failure_tags") or []:
        print(f"  - {item['tag']}: {item['count']}")
    print(f"\nReport: {path}")
    print(f"Markdown: {path.with_suffix('.md')}")


if __name__ == "__main__":
    main()
