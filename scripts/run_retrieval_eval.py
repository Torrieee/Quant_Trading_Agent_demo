"""运行检索评测与消融实验。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from quant_agent.eval.retrieval_eval import (  # noqa: E402
    DEFAULT_RETRIEVAL_EVALSET,
    run_retrieval_eval,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run retrieval eval with ablation")
    parser.add_argument("--evalset", type=Path, default=DEFAULT_RETRIEVAL_EVALSET)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "eval_retrieval_v1.json",
    )
    args = parser.parse_args()

    report = run_retrieval_eval(args.evalset, k=args.k)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Evalset: {report['evalset_id']} symbol={report['symbol']}")
    print(f"Recall@{args.k} / MRR ablation:")
    for row in report["ablation"]:
        print(
            f"  {row['variant']:16s}  recall@{args.k}={row[f'recall@{args.k}']:.3f}  "
            f"mrr={row['mrr']:.3f}"
        )
    bench = report["benchmark"]
    mark = "PASS" if bench["passed"] else "FAIL"
    print(f"\nBenchmark ({bench['primary_variant']}): {mark}")
    print(f"Report: {args.output}")

    if not bench["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
