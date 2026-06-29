#!/usr/bin/env python3
"""生成完整韧性演示 trace：timeout → retry → verifier fail → replan → HITL → resume。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from quant_agent.observability.showcase import NARRATIVE, run_showcase_resilience


def main() -> None:
    result = run_showcase_resilience(project_root=PROJECT_ROOT, export=True)
    print(f"Showcase: {result['case_id']}")
    print(f"Success: {result['success']}")
    print(f"Steps: {len(result['trace_steps'])}")
    if result.get("trace_path"):
        print(f"Trace: {result['trace_path']}")
    if result.get("insights_path"):
        print(f"Insights: {result['insights_path']}")
    print("\n--- 口述时间线 ---")
    for line in NARRATIVE:
        print(line)

    out = PROJECT_ROOT / "reports" / "showcase_resilience_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nSummary: {out}")


if __name__ == "__main__":
    main()
