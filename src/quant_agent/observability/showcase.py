"""韧性演示链路：生成可演示讲解的完整 trace。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from .. import QuantEngine
from ..runtime.tool_adapter import HarnessToolAdapter
from ..runtime.tool_policy import ToolExecutionPolicy
from ..ui.demo_model import DemoChatModel, load_fixture_analysis_data
from .trace_analysis import analyze_traces, write_trace_insights_report
from .tracer import export_trace

SHOWCASE_CASE_ID = "showcase_resilience"
NARRATIVE = [
    "1. Supervisor 进入 Research（动态子图）",
    "2. Planner 生成 market + evidence 并行任务",
    "3. LangGraph Send 并行执行 research_market / research_evidence",
    "4. strategy 工具首次 timeout → ToolPolicy retry 成功",
    "5. Verifier 首次失败（showcase gate）→ replan",
    "6. 第二次 Planner → Workers → Verifier 通过",
    "7. Risk 前 HITL interrupt",
    "8. resume(human_approval=pass) → Reporter 完成报告",
]


def run_showcase_resilience(
    *,
    project_root: Path | None = None,
    export: bool = True,
) -> dict[str, Any]:
    root = project_root or Path.cwd()
    adapter = HarnessToolAdapter(policy=ToolExecutionPolicy(max_retries=2))
    adapter.set_fault_injection(
        {
            "type": "tool_timeout",
            "tool_name": "get_strategy_recommendation",
            "fail_count": 1,
            "error_code": "tool_timeout",
        }
    )

    engine = QuantEngine(
        adapter=adapter,
        model=DemoChatModel(),
        checkpointer=MemorySaver(),
        enable_checkpoint=True,
    )

    symbol = "FIXTURE"
    gate = {
        "require_human_approval": True,
        "force_research_replan_once": True,
        "max_replan": 1,
        "max_steps": 20,
        "expect_report": True,
    }

    phase1 = engine.analyze(
        symbol,
        task="评估 FIXTURE 供应链风险，推荐策略并完成风控（韧性演示）",
        gate=gate,
        analysis_data=load_fixture_analysis_data(symbol),
        case_id=SHOWCASE_CASE_ID,
        thread_id=SHOWCASE_CASE_ID,
        enable_dynamic_research=True,
        export_trace=False,
    )

    all_steps = list(phase1.trace_steps)
    if phase1.interrupted:
        all_steps.append(
            {
                "agent": "hitl",
                "tool_name": "human_approval",
                "arguments": {"interrupt_at": "risk"},
                "observation": {"status": "pending"},
                "status": "ok",
                "hitl": True,
                "rationale": "Risk 前静态 interrupt_before，等待人工审批",
            }
        )

    phase2 = engine.resume(
        symbol,
        case_id=SHOWCASE_CASE_ID,
        thread_id=SHOWCASE_CASE_ID,
        human_approval="pass",
    )
    all_steps.extend(phase2.trace_steps)
    all_steps.append(
        {
            "agent": "hitl",
            "tool_name": "human_approval_resume",
            "arguments": {"decision": "pass"},
            "observation": {"resumed": True},
            "status": "ok",
            "rationale": "人工批准后 resume 继续 Risk → Reporter",
        }
    )

    payload: dict[str, Any] = {
        "case_id": SHOWCASE_CASE_ID,
        "symbol": symbol,
        "success": phase2.success and bool(phase2.report),
        "trace_steps": all_steps,
        "final_state": phase2.final_state,
        "extra": {
            "showcase": True,
            "narrative": NARRATIVE,
            "phases": {
                "phase1_interrupted": phase1.interrupted,
                "phase2_risk_verdict": phase2.risk_verdict,
                "agents_visited": phase2.agents_visited,
            },
        },
    }

    if export:
        trace_path = export_trace(
            case_id=SHOWCASE_CASE_ID,
            symbol=symbol,
            trace_steps=all_steps,
            final_state=phase2.final_state,
            extra=payload["extra"],
        )
        report = analyze_traces(root / "data_cache" / "traces")
        write_trace_insights_report(report, root / "reports" / "trace_insights.json")
        payload["trace_path"] = str(trace_path)
        payload["insights_path"] = str(root / "reports" / "trace_insights.json")

    return payload
