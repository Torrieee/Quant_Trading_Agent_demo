"""编译 Research 动态子图（Planner → Send 并行 Workers → Verifier → [Replan] → Synthesizer）。"""



from __future__ import annotations



from typing import Any, Literal



from langgraph.graph import END, StateGraph

from langgraph.types import Send



from ...runtime.tool_adapter import HarnessToolAdapter

from ..state import WorkflowState

from .planner import build_research_plan

from .research_subgraph_state import ResearchSubgraphState

from .synthesizer import synthesize_research

from .verifier import verify_research

from .workers import execute_worker_task



# 可并行执行的 Worker 类型（market + evidence 双路 Send）

_PARALLEL_WORKERS = frozenset({"evidence", "market"})





def _planner_node(state: ResearchSubgraphState) -> ResearchSubgraphState:

    plan = build_research_plan(state)

    replan = int(state.get("replan_count") or 0)

    trace = [

        {

            "agent": "research_planner",

            "tool_name": "plan_tasks",

            "arguments": {

                "replan_count": replan,

                "task_count": len(plan),

                "parallel_workers": [p["worker"] for p in plan if p.get("worker") in _PARALLEL_WORKERS],

            },

            "observation": {"plan": [p.get("worker") for p in plan]},

            "latency_ms": 0.0,

            "status": "ok",

            "rationale": "规则 Planner；market/evidence 将经 Send 并行调度",

        }

    ]

    return ResearchSubgraphState(

        research_plan=plan,

        trace_steps=trace,

        step_count=1,

    )





def _dispatch_parallel_workers(state: ResearchSubgraphState) -> list[Send]:

    """Map：对 plan 中 market/evidence 发 Send；其余在 join 后顺序执行。"""

    plan = list(state.get("research_plan") or [])

    base_quant = dict(state.get("quant_state") or {})

    sends: list[Send] = []

    for task in plan:

        if task.get("worker") in _PARALLEL_WORKERS:

            sends.append(

                Send(

                    "research_worker",

                    {

                        "symbol": state.get("symbol"),

                        "task": state.get("task"),

                        "gate": state.get("gate") or {},

                        "quant_state": base_quant,

                        "worker_task": task,

                    },

                )

            )

    if not sends:

        # 无并行任务时退化为单 Send

        if plan:

            sends.append(

                Send(

                    "research_worker",

                    {

                        "symbol": state.get("symbol"),

                        "task": state.get("task"),

                        "gate": state.get("gate") or {},

                        "quant_state": base_quant,

                        "worker_task": plan[0],

                    },

                )

            )

    return sends





def _make_worker_node(adapter: HarnessToolAdapter):

    def worker_node(state: ResearchSubgraphState) -> ResearchSubgraphState:

        return ResearchSubgraphState(**execute_worker_task(state, adapter))



    return worker_node





def _join_node(state: ResearchSubgraphState) -> ResearchSubgraphState:

    findings = state.get("research_findings") or []

    return ResearchSubgraphState(

        trace_steps=[

            {

                "agent": "research_workers_join",

                "tool_name": "parallel_join",

                "arguments": {},

                "observation": {

                    "parallel_workers": [f.get("worker") for f in findings],

                    "count": len(findings),

                },

                "latency_ms": 0.0,

                "status": "ok",

                "rationale": "LangGraph Send 并行 Worker 汇合",

                "parallel": True,

            }

        ],

        step_count=1,

    )





def _route_after_join(

    state: ResearchSubgraphState,

) -> Literal["research_worker_sequential", "research_verifier"]:

    plan = list(state.get("research_plan") or [])

    done = {f.get("worker") for f in state.get("research_findings") or []}

    pending = [t for t in plan if t.get("worker") not in done and t.get("worker") not in _PARALLEL_WORKERS]

    if pending:

        return "research_worker_sequential"

    return "research_verifier"





def _make_sequential_worker(adapter: HarnessToolAdapter):

    def sequential_node(state: ResearchSubgraphState) -> ResearchSubgraphState:

        plan = list(state.get("research_plan") or [])

        done = {f.get("worker") for f in state.get("research_findings") or []}

        pending = [t for t in plan if t.get("worker") not in done and t.get("worker") not in _PARALLEL_WORKERS]

        if not pending:

            return ResearchSubgraphState()

        return ResearchSubgraphState(**execute_worker_task({**state, "worker_task": pending[0]}, adapter))



    return sequential_node





def _verifier_node(state: ResearchSubgraphState) -> ResearchSubgraphState:

    verification = verify_research(state)

    trace = [

        {

            "agent": "research_verifier",

            "tool_name": "verify_findings",

            "arguments": {},

            "observation": verification,

            "latency_ms": 0.0,

            "status": "ok" if verification.get("passed") else "warn",

            "rationale": "规则验证研究产出",

        }

    ]

    failures: list[str] = []

    if not verification.get("passed"):

        failures.extend([f"research_verify: {m}" for m in verification.get("missing") or []])

    return ResearchSubgraphState(

        research_verification=verification,

        trace_steps=trace,

        failures=failures,

        step_count=1,

    )





def _synthesizer_node(state: ResearchSubgraphState) -> ResearchSubgraphState:

    quant = synthesize_research(state)

    return ResearchSubgraphState(

        quant_state=quant,

        trace_steps=[

            {

                "agent": "research_synthesizer",

                "tool_name": "synthesize",

                "arguments": {},

                "observation": {"summary_len": len(quant.get("research_summary") or "")},

                "latency_ms": 0.0,

                "status": "ok",

                "rationale": "合并 findings 写入 quant_state",

            }

        ],

        research_complete=True,

        step_count=1,

    )





def _route_after_verify(

    state: ResearchSubgraphState,

) -> Literal["research_replan_bump", "research_synthesizer"]:

    verification = state.get("research_verification") or {}

    if verification.get("passed"):

        return "research_synthesizer"

    replan = int(state.get("replan_count") or 0)

    max_replan = int(state.get("max_replan") or 1)

    if replan >= max_replan:

        return "research_synthesizer"

    return "research_replan_bump"





def _replan_bump_node(state: ResearchSubgraphState) -> ResearchSubgraphState:

    return ResearchSubgraphState(

        replan_count=int(state.get("replan_count") or 0) + 1,

        research_findings=[],

        trace_steps=[

            {

                "agent": "research_replan_bump",

                "tool_name": "replan_bump",

                "arguments": {"replan_count": int(state.get("replan_count") or 0) + 1},

                "observation": {},

                "latency_ms": 0.0,

                "status": "ok",

                "rationale": "Verifier 未通过，清空 findings 后重规划",

            }

        ],

        step_count=1,

    )





def build_research_subgraph(adapter: HarnessToolAdapter) -> Any:

    """编译 Research 子图；并行 Worker 使用 LangGraph Send + reducer。"""

    graph = StateGraph(ResearchSubgraphState)

    graph.add_node("research_planner", _planner_node)

    graph.add_node("research_worker", _make_worker_node(adapter))

    graph.add_node("research_workers_join", _join_node)

    graph.add_node("research_worker_sequential", _make_sequential_worker(adapter))

    graph.add_node("research_verifier", _verifier_node)

    graph.add_node("research_replan_bump", _replan_bump_node)

    graph.add_node("research_synthesizer", _synthesizer_node)



    graph.set_entry_point("research_planner")

    graph.add_conditional_edges("research_planner", _dispatch_parallel_workers, ["research_worker"])

    graph.add_edge("research_worker", "research_workers_join")

    graph.add_conditional_edges(

        "research_workers_join",

        _route_after_join,

        {

            "research_worker_sequential": "research_worker_sequential",

            "research_verifier": "research_verifier",

        },

    )

    graph.add_edge("research_worker_sequential", "research_verifier")

    graph.add_conditional_edges(

        "research_verifier",

        _route_after_verify,

        {

            "research_replan_bump": "research_replan_bump",

            "research_synthesizer": "research_synthesizer",

        },

    )

    graph.add_edge("research_replan_bump", "research_planner")

    graph.add_edge("research_synthesizer", END)

    return graph.compile()





def run_dynamic_research(

    state: WorkflowState,

    adapter: HarnessToolAdapter,

) -> WorkflowState:

    """执行动态 Research 子图并合并回 WorkflowState。"""

    gate = state.get("gate") or {}

    enriched: ResearchSubgraphState = ResearchSubgraphState(

        symbol=state.get("symbol"),

        task=state.get("task"),

        gate=gate,

        quant_state=dict(state.get("quant_state") or {}),

        replan_count=int(state.get("replan_count") or 0),

        max_replan=int(gate.get("max_replan", state.get("max_replan") or 1)),

        research_plan=[],

        research_findings=[],

        research_verification=None,

        trace_steps=list(state.get("trace_steps") or []),

        failures=list(state.get("failures") or []),

        step_count=int(state.get("step_count") or 0),

    )

    app = build_research_subgraph(adapter)

    result = app.invoke(enriched)

    visited = list(state.get("agents_visited") or [])

    if "research" not in visited:

        visited.append("research")

    return WorkflowState(

        quant_state=result.get("quant_state"),

        trace_steps=result.get("trace_steps"),

        agents_visited=visited,

        step_count=result.get("step_count", state.get("step_count", 0)),

        research_complete=True,

        research_plan=result.get("research_plan"),

        research_findings=result.get("research_findings"),

        research_verification=result.get("research_verification"),

        replan_count=result.get("replan_count"),

        failures=result.get("failures"),

    )


