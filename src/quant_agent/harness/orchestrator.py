"""Agent Harness orchestrator: Perception -> Planner -> Executor -> Evaluator -> Reflection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..llm_agent import TradingFunctionCaller
from .evaluators.efficiency import evaluate_efficiency
from .evaluators.evidence_coverage import evaluate_evidence_coverage
from .evaluators.llm_judge import LLMJudge
from .executor import Executor
from .llm_client import DEFAULT_LIVE_MODEL, get_openai_client
from .planner import OfflinePlanner, select_planner
from .reflection import resolve_retry_plan
from .tool_adapter import HarnessToolAdapter
from .trace import AgentTrace, new_trace_id
from .trace_store import TraceStore

HARNESS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = HARNESS_ROOT.parents[2]
DEFAULT_TRACE_DIR = PROJECT_ROOT / "reports" / "traces"


def _evaluate_attempt(
    state: dict[str, Any],
    trace: AgentTrace,
    gate: dict[str, Any],
    exec_errors: list[str],
) -> dict[str, Any]:
    evidence = evaluate_evidence_coverage(state, gate)
    efficiency = evaluate_efficiency(trace.steps, gate, exec_errors=exec_errors)

    failures: list[str] = []
    failures.extend(evidence["failures"])
    failures.extend(efficiency["failures"])

    for key in gate.get("expected_final_keys") or []:
        if key not in state:
            failures.append(f"gate: missing expected key '{key}' in final state")

    if gate.get("expect_plan_over_max"):
        if not any("max_steps_exceeded" in f for f in failures):
            failures.append("gate: expected plan to exceed max_steps but it did not")

    evaluations = {
        "evidence_coverage": evidence,
        "efficiency": efficiency,
    }
    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "evaluations": evaluations,
    }


class AgentHarnessOrchestrator:
    def __init__(
        self,
        *,
        adapter: HarnessToolAdapter | None = None,
        planner: OfflinePlanner | None = None,
        trace_dir: Path | None = None,
        live: bool = False,
        llm_client: Any | None = None,
        model: str = DEFAULT_LIVE_MODEL,
        llm_judge: LLMJudge | None = None,
    ) -> None:
        self.adapter = adapter or HarnessToolAdapter()
        self.offline_planner = planner or OfflinePlanner()
        self.trace_dir = trace_dir or DEFAULT_TRACE_DIR
        self.trace_store = TraceStore(self.trace_dir)
        self.live = live
        self.llm_client = llm_client if live else None
        if self.live and self.llm_client is None:
            self.llm_client = get_openai_client()
        self.model = model
        self._caller = self.adapter.caller
        self.llm_judge = llm_judge
        if self.live and self.llm_judge is None:
            self.llm_judge = LLMJudge(self.llm_client, model=model)

    def run_case(self, case: dict[str, Any], *, write_trace: bool = True) -> dict[str, Any]:
        case_id = case["name"]
        gate = case.get("gate", {})
        max_steps = gate.get("max_steps", 6)
        planner = select_planner(
            case,
            live=self.live,
            caller=self._caller,
            client=self.llm_client,
            offline=self.offline_planner,
        )

        first = self._run_attempt(
            case,
            plan=planner.build_plan(case),
            attempt=1,
            max_steps=max_steps,
        )
        attempts: list[dict[str, Any]] = [first]
        final = first
        first_attempt_failed = False
        reflection_mode = "none"

        retry_plan, reason, reflection_mode = resolve_retry_plan(
            case,
            first["evaluations"],
            live=self.live,
            trace=first["trace"].to_dict(),
            caller=self._caller,
            client=self.llm_client,
        )
        if retry_plan:
            child = self._run_attempt(
                case,
                plan=retry_plan,
                parent_trace_id=first["trace"].trace_id,
                attempt=2,
                max_steps=max_steps,
                reflection_triggered=True,
                reflection_reason=reason,
                initial_state=dict(first["final_state"]),
            )
            attempts.append(child)
            final = child
            if not first["passed"]:
                first_attempt_failed = True

        if write_trace:
            for att in attempts:
                self.trace_store.save(att["trace"])

        result: dict[str, Any] = {
            "case_id": case_id,
            "type": "agent_task",
            "mode": "live" if self.live else case.get("mode", "offline"),
            "passed": final["passed"],
            "failures": final["failures"],
            "final_state": final["final_state"],
            "trace": final["trace"].to_dict(),
            "step_count": len(final["trace"].steps),
            "evaluations": final["evaluations"],
            "first_attempt_failed": first_attempt_failed,
            "reflection_mode": reflection_mode,
            "attempts": [
                {
                    "attempt": a["trace"].attempt,
                    "passed": a["passed"],
                    "failures": a["failures"],
                    "trace_id": a["trace"].trace_id,
                    "parent_trace_id": a["trace"].parent_trace_id,
                    "reflection_triggered": a["trace"].reflection_triggered,
                    "reflection_reason": a["trace"].reflection_reason,
                    "evaluations": a["evaluations"],
                }
                for a in attempts
            ],
        }

        if self.live and self.llm_judge is not None and case.get("live_judge_enabled", True):
            result["llm_judge"] = self.llm_judge.evaluate(
                case,
                final["trace"].to_dict(),
                rule_evaluations=final["evaluations"],
            )

        return result

    def _run_attempt(
        self,
        case: dict[str, Any],
        *,
        plan: list[dict[str, Any]],
        parent_trace_id: str | None = None,
        attempt: int = 1,
        max_steps: int = 6,
        reflection_triggered: bool = False,
        reflection_reason: str | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        trace = AgentTrace(
            trace_id=new_trace_id(),
            case_id=case["name"],
            parent_trace_id=parent_trace_id,
            attempt=attempt,
            reflection_triggered=reflection_triggered,
            reflection_reason=reflection_reason,
        )
        executor = Executor(self.adapter, max_steps=max_steps)
        state, exec_errors = executor.run_plan(
            plan,
            trace,
            initial_state=initial_state,
            rationale_prefix=f"Execute {case['name']} attempt {attempt}",
        )
        gate = case.get("gate", {})
        eval_result = _evaluate_attempt(state, trace, gate, exec_errors)
        return {
            "passed": eval_result["passed"],
            "failures": eval_result["failures"],
            "evaluations": eval_result["evaluations"],
            "final_state": state,
            "trace": trace,
        }
