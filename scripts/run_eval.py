"""运行 Agent 回归评测并输出 scorecard。"""



from __future__ import annotations



import argparse

import sys

from pathlib import Path



PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT / "src"))



from quant_agent.eval.runner import (  # noqa: E402

    DEFAULT_EVALSET,

    DEFAULT_LIVE_EVALSET,

    AgentEvalRunner,

    write_eval_markdown,

    write_eval_report,

)





def main() -> None:

    parser = argparse.ArgumentParser(description="Run QuantEngine agent eval")

    parser.add_argument(

        "--evalset",

        type=Path,

        default=None,

        help="Evalset YAML path (default: regression_v1 or capability_v1 with --live)",

    )

    parser.add_argument(

        "--live",

        action="store_true",

        help="Run live capability eval (DeepSeek API, capability_v1.yaml)",

    )

    parser.add_argument(

        "--output",

        type=Path,

        default=None,

        help="JSON scorecard output path",

    )

    parser.add_argument("--trace", action="store_true", help="Write per-case traces")

    parser.add_argument(

        "--judge",

        action="store_true",

        help="Enable LLM-as-judge (live evalsets only)",

    )

    parser.add_argument(

        "--no-judge",

        action="store_true",

        help="Disable LLM-as-judge even if evalset benchmark requests it",

    )

    args = parser.parse_args()



    evalset = args.evalset

    if evalset is None:

        evalset = DEFAULT_LIVE_EVALSET if args.live else DEFAULT_EVALSET



    output = args.output

    if output is None:

        output = (

            PROJECT_ROOT / "reports" / "eval_capability_v1.json"

            if args.live or str(evalset).endswith("capability_v1.yaml")

            else PROJECT_ROOT / "reports" / "eval_regression_v1.json"

        )



    enable_judge = None

    if args.judge:

        enable_judge = True

    if args.no_judge:

        enable_judge = False



    report = AgentEvalRunner(evalset_path=evalset).run_evalset(

        write_trace=args.trace,

        enable_judge=enable_judge,

    )

    write_eval_report(report, output)

    md_path = output.with_suffix(".md")

    write_eval_markdown(report, md_path)



    sc = report["scorecard"]

    s = sc["summary"]

    print(f"Evalset: {sc['evalset_id']} ({sc['mode']})")

    print(f"Pass: {s['passed']}/{sc['case_count']} ({s['pass_rate']:.0%})")

    print(f"Mean steps: {s['mean_steps']}")

    print()

    print("By bucket:")

    for bucket, stats in sorted(sc.get("by_bucket", {}).items()):

        print(f"  {bucket}: {stats['passed']}/{stats['total']} ({stats['pass_rate']:.0%})")



    js = report.get("judge_summary")

    if js and js.get("judged_cases"):

        print()

        print(f"LLM Judge: {js['judged_cases']} cases, mean={js.get('mean_overall')}")



    bench = report.get("benchmark") or {}

    if bench:

        mark = "PASS" if bench.get("passed") else "FAIL"

        print(f"Benchmark gate: {mark}")

        for f in bench.get("failures") or []:

            print(f"  - {f}")



    failed = [c for c in sc.get("cases", []) if not c["passed"]]

    if failed:

        print()

        print("Failed cases:")

        for c in failed:

            print(f"  - {c['name']}: {c.get('failures')}")

    print()

    print(f"Report: {output}")

    print(f"Markdown: {md_path}")



    exit_failed = s["failed"] > 0 or not bench.get("passed", True)

    if exit_failed:

        raise SystemExit(1)





if __name__ == "__main__":

    main()

