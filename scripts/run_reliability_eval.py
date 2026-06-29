"""运行可靠性评测（Fake Model：故障恢复 + 不可信上下文）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from quant_agent.eval.reliability import (  # noqa: E402
    DEFAULT_RELIABILITY_EVALSET,
    run_reliability_eval,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run agent reliability eval")
    parser.add_argument("--evalset", type=Path, default=DEFAULT_RELIABILITY_EVALSET)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "eval_reliability_v1.json",
    )
    args = parser.parse_args()

    report = run_reliability_eval(args.evalset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    s = report["summary"]
    print(f"Evalset: {report['evalset_id']} ({report['mode']}) — {report.get('eval_focus', 'reliability')}")
    print(f"Cases: {s['passed_cases']}/{s['total_cases']} pass (rate {s['case_pass_rate']:.0%})")
    for case in report["results"]:
        mark = "PASS" if case["passed"] else "FAIL"
        rep = case["repeat"]
        pow_key = f"pass^{rep}"
        print(
            f"  {case['name']} [{mark}] {pow_key}="
            f"{case.get(pow_key, 0):.0%} success_rate={case['success_rate']:.0%}"
        )
        if case.get("fault_injection"):
            print(f"    max_retry_observed={case.get('retry_observed_max', 0)}")

    bench = report["benchmark"]
    mark = "PASS" if bench["passed"] else "FAIL"
    print(f"\nBenchmark gate: {mark}")
    print(f"Report: {args.output}")

    if not bench["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
