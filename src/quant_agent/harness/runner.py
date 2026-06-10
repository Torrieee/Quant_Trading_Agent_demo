"""Harness runner: load YAML cases, execute, emit JSON report."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from ..agent import AgentConfig, TradingAgent
from ..config import BacktestConfig, DataConfig, StrategyConfig
from ..features import add_daily_returns
from ..llm_agent import TradingFunctionCaller
from .evaluators.process_quality import build_process_trace, validate_process_trace
from .evaluators.result_quality import validate_result_quality
from .evaluators.tool_compliance import run_tool_compliance_checks, validate_tool_schemas
from .orchestrator import AgentHarnessOrchestrator
from .tool_adapter import HarnessToolAdapter

HARNESS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = HARNESS_ROOT.parents[2]
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
CASES_DIR = HARNESS_ROOT / "cases"


def load_fixture(name: str) -> pd.DataFrame:
    path = FIXTURES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if "ret" not in df.columns:
        df = add_daily_returns(df)
    return df


def _load_yaml_cases(filename: str) -> list[dict[str, Any]]:
    path = CASES_DIR / filename
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data or []


class HarnessRunner:
    def __init__(self, *, live: bool = False) -> None:
        self.live = live
        self.caller = TradingFunctionCaller()
        self.orchestrator = AgentHarnessOrchestrator(
            adapter=HarnessToolAdapter(self.caller),
            live=live,
        )

    def run_agent_task_case(
        self, case: dict[str, Any], *, write_trace: bool = True
    ) -> dict[str, Any]:
        return self.orchestrator.run_case(case, write_trace=write_trace)

    def run_backtest_case(self, case: dict[str, Any]) -> dict[str, Any]:
        case_id = case["name"]
        fixture_name = case["fixture"]
        strategy = case["strategy"]
        gate = case.get("gate", {})
        report_only = case.get("report_only", {})

        df = load_fixture(fixture_name)

        def mock_download(_cfg: DataConfig) -> pd.DataFrame:
            return df.copy()

        import quant_agent.agent as agent_module

        original = agent_module.download_ohlcv
        agent_module.download_ohlcv = mock_download
        try:
            cfg = AgentConfig(
                data=DataConfig(symbol="FIXTURE", start=date(2020, 1, 1)),
                strategy=StrategyConfig(name=strategy),
                backtest=BacktestConfig(initial_cash=100_000),
            )
            agent = TradingAgent(cfg)
            trace = build_process_trace(agent, case_id)
            process_result = validate_process_trace(trace)

            stats = trace.get("final_metrics", {})
            required_stats = gate.get(
                "required_stats",
                [
                    "total_return",
                    "sharpe",
                    "max_drawdown",
                    "num_days",
                    "num_trades",
                    "win_rate",
                ],
            )
            result_result = validate_result_quality(
                stats,
                min_days=gate.get("min_days", 100),
                required_stats=required_stats,
            )

            passed = process_result["passed"] and result_result["passed"]
            report_metrics = {
                k: stats.get(k)
                for k in report_only.get("metrics", [])
                if k in stats
            }

            return {
                "case_id": case_id,
                "type": "backtest",
                "passed": passed,
                "process_trace": {
                    k: v
                    for k, v in trace.items()
                    if not k.startswith("_")
                },
                "process_quality": process_result,
                "result_quality": result_result,
                "report_only": report_metrics,
            }
        finally:
            agent_module.download_ohlcv = original

    def run_tool_case(self, case: dict[str, Any]) -> dict[str, Any]:
        schema_result = validate_tool_schemas(self.caller.get_available_functions())
        case_result = run_tool_compliance_checks(self.caller, case)
        passed = schema_result["passed"] and case_result["passed"]
        return {
            "case_id": case["name"],
            "type": "tool_compliance",
            "passed": passed,
            "schema_quality": schema_result,
            "tool_case": case_result,
        }

    def run_all(self) -> dict[str, Any]:
        results: list[dict[str, Any]] = []

        for case in _load_yaml_cases("backtest_cases.yaml"):
            results.append(self.run_backtest_case(case))

        for case in _load_yaml_cases("llm_tool_cases.yaml"):
            results.append(self.run_tool_case(case))

        for case in _load_yaml_cases("tool_chain_cases.yaml"):
            if case.get("harness", True):
                results.append(self.run_agent_task_case(case))

        passed = sum(1 for r in results if r["passed"])
        failed = len(results) - passed
        return {
            "run_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "live" if self.live else "offline",
            "summary": {
                "passed": passed,
                "failed": failed,
                "pass_rate": passed / len(results) if results else 1.0,
                "total": len(results),
            },
            "cases": results,
        }


def run_harness(
    *,
    report_path: Path | None = None,
    gate: bool = False,
    live: bool = False,
) -> dict[str, Any]:
    report = HarnessRunner(live=live).run_all()
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    if gate and report["summary"]["failed"] > 0:
        raise SystemExit(1)
    return report
