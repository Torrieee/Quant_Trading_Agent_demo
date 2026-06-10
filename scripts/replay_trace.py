"""Replay stored trace through offline evaluators (log replay, no API)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from quant_agent.harness.replay import replay_trace_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay trace through offline evaluators")
    parser.add_argument("trace_file", type=Path, help="Path to trace JSON")
    parser.add_argument(
        "--required-evidence-keys",
        nargs="*",
        default=[],
        help="Override required evidence keys for replay",
    )
    args = parser.parse_args()
    gate = {"required_evidence_keys": args.required_evidence_keys}
    result = replay_trace_file(args.trace_file, gate)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
