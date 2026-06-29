"""兼容层：运行时执行器（DeepSeek API 在线模式）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ..engine import QuantEngine
from ..features import add_daily_returns
from ..harness.evaluators.efficiency import evaluate_efficiency
from ..harness.evaluators.evidence_coverage import evaluate_evidence_coverage
from ..harness.tool_adapter import HarnessToolAdapter
from ..harness.trace import AgentTrace, AgentTraceRecord, new_trace_id
from ..harness.trace_store import TraceStore
from ..agents.llm import DeepSeekConfigError, require_deepseek_chat_model

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRACE_DIR = PROJECT_ROOT / "reports" / "traces"
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


class RuntimeRunner:
    """执行 YAML case 或 ad-hoc 任务，输出 Harness 兼容结果。"""

    def __init__(
        self,
        *,
        adapter: HarnessToolAdapter | None = None,
        trace_dir: Path | None = None,
        model: Any | None = None,
    ) -> None:
        self.adapter = adapter or HarnessToolAdapter()
        self.trace_dir = trace_dir or DEFAULT_TRACE_DIR
        self.trace_store = TraceStore(self.trace_dir)
        self.model = model

    def run_case(self, case: dict[str, Any], *, write_trace: bool = True) -> dict[str, Any]:
        case_id = case["name"]
        gate = case.get("gate", {})
        task = case.get("task") or case.get("task_hint") or case_id
        symbol = case.get("symbol", "AAPL")

        model = self.model
        if model is None:
            try:
                model = require_deepseek_chat_model()
            except DeepSeekConfigError as exc:
                return self._error_result(case_id, str(exc))

        analysis_data = case.get("analysis_data")
        if analysis_data is None and case.get("fixture"):
            analysis_data = _load_fixture_analysis_data(case["fixture"], symbol)

        flags = case.get("workflow_flags") or {}
        engine = QuantEngine(adapter=self.adapter, model=model)
        engine_result = engine.analyze(
            symbol,
            task=task,
            gate=gate,
            analysis_data=analysis_data,
            case_id=case_id,
            include_fundamental=flags.get("include_fundamental", True),
            include_sentiment=flags.get("include_sentiment", True),
            include_research_analyst=flags.get("include_research_analyst", True),
        )

        final = engine_result.raw
        quant_state = engine_result.final_state
        trace_steps = engine_result.trace_steps
        exec_errors = list(final.get("failures") or [])
        if engine_result.error:
            exec_errors.append(engine_result.error)

        if not gate.get("expect_risk_pass", True) and engine_result.risk_verdict == "reject":
            exec_errors = [e for e in exec_errors if not e.startswith("risk:")]

        agent_trace = self._build_agent_trace(case_id, trace_steps, final)
        evidence = evaluate_evidence_coverage(quant_state, gate)
        efficiency = evaluate_efficiency(
            [_tool_step_to_trace_record(i + 1, s) for i, s in enumerate(trace_steps)],
            gate,
            exec_errors=exec_errors,
        )

        failures: list[str] = []
        failures.extend(evidence["failures"])
        failures.extend(efficiency["failures"])
        failures.extend(exec_errors)

        expected_agents = gate.get("expected_agents") or [
            "analysis_panel",
            "research",
            "risk",
            "reporter",
        ]
        visited = engine_result.agents_visited
        for agent in expected_agents:
            if agent not in visited:
                failures.append(f"runtime: 缺少预期智能体 '{agent}'")

        if engine_result.risk_verdict == "reject" and gate.get("expect_risk_pass", True):
            failures.append(f"runtime: 风控拒绝 — {engine_result.risk_reason}")

        if gate.get("expect_report") and not engine_result.report:
            failures.append("runtime: 缺少报告")

        for key in gate.get("expected_final_keys") or []:
            if key not in quant_state:
                failures.append(f"gate: final_state 缺少 '{key}'")

        if gate.get("expect_preliminary_decision") and not engine_result.decision:
            failures.append("gate: 缺少 preliminary_decision")

        passed = len(failures) == 0

        if write_trace:
            self.trace_store.save(agent_trace)

        return {
            "case_id": case_id,
            "type": "runtime_multi_agent",
            "mode": "api",
            "passed": passed,
            "failures": failures,
            "final_state": quant_state,
            "report": engine_result.report,
            "risk_verdict": engine_result.risk_verdict,
            "agents_visited": visited,
            "trace": agent_trace.to_dict(),
            "step_count": len(trace_steps),
            "evaluations": {
                "evidence_coverage": evidence,
                "efficiency": efficiency,
            },
            "preliminary_decision": engine_result.decision,
            "individual_signals": engine_result.individual_signals,
        }

    def _error_result(self, case_id: str, message: str) -> dict[str, Any]:
        return {
            "case_id": case_id,
            "type": "runtime_multi_agent",
            "mode": "api",
            "passed": False,
            "failures": [message],
            "final_state": {},
            "report": None,
            "risk_verdict": None,
            "agents_visited": [],
            "trace": {},
            "step_count": 0,
            "evaluations": {},
        }

    def _build_agent_trace(
        self,
        case_id: str,
        trace_steps: list[dict[str, Any]],
        final: dict[str, Any],
    ) -> AgentTrace:
        trace = AgentTrace(
            trace_id=new_trace_id(),
            case_id=case_id,
            parent_trace_id=None,
            attempt=1,
            reflection_triggered=False,
            reflection_reason=None,
        )
        for idx, step in enumerate(trace_steps):
            tool_name = step.get("tool_name") or step.get("agent") or "unknown"
            trace.steps.append(
                AgentTraceRecord(
                    step_id=idx + 1,
                    rationale=step.get("rationale"),
                    tool_name=str(tool_name),
                    arguments=dict(step.get("arguments") or {}),
                    observation=step.get("observation") or {},
                    status=step.get("status", "ok"),
                    latency_ms=float(step.get("latency_ms") or 0.0),
                )
            )
        if final.get("report"):
            trace.steps.append(
                AgentTraceRecord(
                    step_id=len(trace.steps) + 1,
                    rationale="Reporter 输出",
                    tool_name="report",
                    arguments={},
                    observation={"report": final["report"][:500]},
                    status="ok",
                    latency_ms=0.0,
                )
            )
        return trace


def _load_fixture_analysis_data(fixture_name: str, symbol: str) -> dict[str, Any]:
    path = FIXTURES_DIR / fixture_name
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if "ret" not in df.columns:
        df = add_daily_returns(df)
    if "Adj Close" not in df.columns and "Close" in df.columns:
        df["Adj Close"] = df["Close"]
    return {
        "historical_data": df,
        "stock_info": {
            "symbol": symbol,
            "pe_ratio": 18.5,
            "pb_ratio": 2.8,
            "dividend_yield": 0.015,
        },
    }


def _tool_step_to_trace_record(step_id: int, step: dict[str, Any]) -> AgentTraceRecord:
    return AgentTraceRecord(
        step_id=step_id,
        rationale=step.get("rationale"),
        tool_name=str(step.get("tool_name") or step.get("agent") or "unknown"),
        arguments=dict(step.get("arguments") or {}),
        observation=step.get("observation") or {},
        status=step.get("status", "ok"),
        latency_ms=float(step.get("latency_ms") or 0.0),
    )


def run_runtime_task(
    task: str,
    *,
    symbol: str = "AAPL",
    gate: dict[str, Any] | None = None,
    model: Any | None = None,
) -> dict[str, Any]:
    case = {
        "name": "ad_hoc_runtime",
        "task": task,
        "symbol": symbol,
        "gate": gate or {"max_steps": 12, "expect_report": True},
    }
    return RuntimeRunner(model=model).run_case(case, write_trace=False)
