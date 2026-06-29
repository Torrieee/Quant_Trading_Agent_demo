"""LangGraph 协调器：分析面板 → 证据检索 → 研究 → [反思] → 风控 → 报告。"""

from __future__ import annotations

from typing import Any, Iterator

from langgraph.graph import END, START, StateGraph

from ..runtime.tool_adapter import HarnessToolAdapter
from ..observability.tracer import export_trace, stream_events_from_graph
from .checkpoint import get_checkpointer, is_checkpoint_enabled, workflow_invoke_config
from .nodes.analysis_panel import analysis_panel_node
from .nodes.document_retrieval import document_retrieval_node
from .nodes.reflection import reflection_node
from .nodes.reporter import make_reporter_node
from .nodes.research import make_research_node
from .nodes.risk import make_risk_node
from .nodes.supervisor import route_supervisor, supervisor_node
from .serialization import sanitize_for_checkpoint, serialize_analysis_data
from .state import WorkflowState, initial_state


def _checkpoint_safe(node_fn):
    def wrapped(state: WorkflowState) -> WorkflowState:
        result = node_fn(state)
        if not result:
            return result
        return sanitize_for_checkpoint(result)

    return wrapped


def _interrupt_nodes(gate: dict[str, Any] | None) -> list[str]:
    """Demo HITL：静态 interrupt_before；生产可改为 approval 节点内 interrupt()。"""
    gate = gate or {}
    if gate.get("require_human_approval"):
        return ["risk"]
    return []


def build_coordinator_graph(
    adapter: HarnessToolAdapter | None = None,
    model: Any | None = None,
    *,
    checkpointer: Any | None = None,
    enable_checkpoint: bool = False,
    interrupt_before: list[str] | None = None,
):
    adapter = adapter or HarnessToolAdapter()
    graph = StateGraph(WorkflowState)

    graph.add_node("supervisor", _checkpoint_safe(supervisor_node))
    graph.add_node("analysis_panel", _checkpoint_safe(analysis_panel_node))
    graph.add_node("document_retrieval", _checkpoint_safe(document_retrieval_node))
    graph.add_node("research", _checkpoint_safe(make_research_node(adapter, model=model)))
    graph.add_node("reflection", _checkpoint_safe(reflection_node))
    graph.add_node("risk", _checkpoint_safe(make_risk_node(adapter, model=model)))
    graph.add_node("reporter", _checkpoint_safe(make_reporter_node(model=model)))

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "analysis_panel": "analysis_panel",
            "document_retrieval": "document_retrieval",
            "research": "research",
            "reflection": "reflection",
            "risk": "risk",
            "reporter": "reporter",
            "__end__": END,
        },
    )
    graph.add_edge("analysis_panel", "supervisor")
    graph.add_edge("document_retrieval", "supervisor")
    graph.add_edge("research", "supervisor")
    graph.add_edge("reflection", "supervisor")
    graph.add_edge("risk", "supervisor")
    graph.add_edge("reporter", END)

    cp = None
    if enable_checkpoint:
        cp = checkpointer if checkpointer is not None else get_checkpointer()
    elif checkpointer is not None:
        cp = checkpointer

    compile_kw: dict[str, Any] = {}
    if cp is not None:
        compile_kw["checkpointer"] = cp
    if interrupt_before:
        compile_kw["interrupt_before"] = interrupt_before
    return graph.compile(**compile_kw)


class AgentCoordinator:
    """Agentic 工作流协调器（LangGraph 固定拓扑 + 代码 Supervisor）。"""

    def __init__(
        self,
        *,
        adapter: HarnessToolAdapter | None = None,
        model: Any | None = None,
        checkpointer: Any | None = None,
        enable_checkpoint: bool | None = None,
    ) -> None:
        self.adapter = adapter or HarnessToolAdapter()
        self.model = model
        if enable_checkpoint is False:
            self.checkpointer = None
        elif checkpointer is not None:
            self.checkpointer = checkpointer
        elif is_checkpoint_enabled():
            self.checkpointer = get_checkpointer()
        else:
            self.checkpointer = None
        self._app = None
        self._interrupt_key: tuple[Any, ...] = ()

    def _get_app(self, gate: dict[str, Any] | None = None):
        gate = gate or {}
        interrupt_key = (gate.get("require_human_approval"),)
        interrupt = _interrupt_nodes(gate) if self.checkpointer else []
        if self._app is None or self._interrupt_key != interrupt_key:
            self._app = build_coordinator_graph(
                self.adapter,
                model=self.model,
                checkpointer=self.checkpointer,
                enable_checkpoint=self.checkpointer is not None,
                interrupt_before=interrupt or None,
            )
            self._interrupt_key = interrupt_key
        return self._app

    def _prepare_state(
        self,
        *,
        case_id: str,
        symbol: str,
        task: str,
        analysis_data: dict[str, Any],
        gate: dict[str, Any] | None,
        workflow_flags: dict[str, bool] | None,
    ) -> WorkflowState:
        state = initial_state(
            case_id=case_id,
            symbol=symbol,
            task=task,
            gate=gate,
            analysis_data=analysis_data,
            workflow_flags=workflow_flags,
        )
        if self.checkpointer is not None:
            state["analysis_data"] = serialize_analysis_data(state.get("analysis_data") or {})
        return state

    def run(
        self,
        *,
        case_id: str,
        symbol: str,
        task: str,
        analysis_data: dict[str, Any],
        gate: dict[str, Any] | None = None,
        workflow_flags: dict[str, bool] | None = None,
        thread_id: str | None = None,
    ) -> WorkflowState:
        gate = gate or {}
        state = self._prepare_state(
            case_id=case_id,
            symbol=symbol,
            task=task,
            analysis_data=analysis_data,
            gate=gate,
            workflow_flags=workflow_flags,
        )
        config = workflow_invoke_config(case_id, thread_id=thread_id) if self.checkpointer else None
        app = self._get_app(gate)
        if config:
            return app.invoke(state, config=config)
        return app.invoke(state)

    def run_stream(
        self,
        *,
        case_id: str,
        symbol: str,
        task: str,
        analysis_data: dict[str, Any],
        gate: dict[str, Any] | None = None,
        workflow_flags: dict[str, bool] | None = None,
        thread_id: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        gate = gate or {}
        state = self._prepare_state(
            case_id=case_id,
            symbol=symbol,
            task=task,
            analysis_data=analysis_data,
            gate=gate,
            workflow_flags=workflow_flags,
        )
        config = workflow_invoke_config(case_id, thread_id=thread_id) if self.checkpointer else None
        app = self._get_app(gate)
        yield from stream_events_from_graph(app, state, config)

    def is_interrupted(self, case_id: str, *, thread_id: str | None = None) -> bool:
        if self.checkpointer is None:
            return False
        app = self._get_app()
        snapshot = app.get_state(workflow_invoke_config(case_id, thread_id=thread_id))
        if snapshot is None:
            return False
        nxt = getattr(snapshot, "next", None)
        return bool(nxt)

    def resume(
        self,
        case_id: str,
        *,
        thread_id: str | None = None,
        human_approval: str = "pass",
    ) -> WorkflowState:
        if self.checkpointer is None:
            raise RuntimeError("resume 需要启用 checkpointer")
        config = workflow_invoke_config(case_id, thread_id=thread_id)
        app = self._get_app()
        if human_approval == "reject":
            app.update_state(
                config,
                {
                    "human_approval": "reject",
                    "risk_verdict": "reject",
                    "risk_reason": "人工审批拒绝",
                    "done": True,
                },
            )
        else:
            app.update_state(config, {"human_approval": "pass"})
        return app.invoke(None, config=config)

    def get_thread_state(self, case_id: str, *, thread_id: str | None = None) -> dict[str, Any] | None:
        if self.checkpointer is None:
            return None
        app = self._get_app()
        snapshot = app.get_state(workflow_invoke_config(case_id, thread_id=thread_id))
        if snapshot is None:
            return None
        values = getattr(snapshot, "values", None)
        return dict(values) if values else None

    def export_run_trace(
        self,
        *,
        case_id: str,
        symbol: str,
        state: dict[str, Any],
    ):
        return export_trace(
            case_id=case_id,
            symbol=symbol,
            trace_steps=list(state.get("trace_steps") or []),
            final_state=dict(state.get("quant_state") or {}),
            extra={"agents_visited": state.get("agents_visited")},
        )


def run_workflow(
    initial: WorkflowState,
    adapter: HarnessToolAdapter | None = None,
    model: Any | None = None,
    *,
    checkpointer: Any | None = None,
    thread_id: str | None = None,
    enable_checkpoint: bool = False,
) -> WorkflowState:
    use_cp = enable_checkpoint or checkpointer is not None
    app = build_coordinator_graph(
        adapter,
        model=model,
        checkpointer=checkpointer,
        enable_checkpoint=use_cp,
    )
    state = dict(initial)
    if use_cp:
        state["analysis_data"] = serialize_analysis_data(state.get("analysis_data") or {})
        case_id = state.get("case_id") or thread_id or "workflow"
        return app.invoke(state, config=workflow_invoke_config(case_id, thread_id=thread_id))
    return app.invoke(state)
