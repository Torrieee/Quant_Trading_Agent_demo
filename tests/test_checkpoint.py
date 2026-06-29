"""LangGraph Checkpoint 测试。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from quant_agent.agents.checkpoint import workflow_invoke_config
from quant_agent.agents.coordinator import AgentCoordinator, build_coordinator_graph
from quant_agent.agents.serialization import hydrate_analysis_data, serialize_analysis_data
from quant_agent.agents.state import initial_state
from quant_agent.features import add_daily_returns


class _MinimalFakeModel:
    """仅用于 checkpoint 冒烟：Research / Risk / Reporter 一次通过。"""

    def __init__(self) -> None:
        self._research_calls = 0
        self._risk_calls = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        system = ""
        for m in messages:
            if getattr(m, "type", None) == "system":
                system = m.content
                break
        if "量化研究智能体" in system:
            self._research_calls += 1
            if self._research_calls > 1:
                return AIMessage(content="Research complete.")
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_strategy_recommendation",
                        "args": {"market_state": "ranging"},
                        "id": "research-1",
                    }
                ],
            )
        if "Risk 智能体" in system or "风控智能体" in system:
            self._risk_calls += 1
            if self._risk_calls > 1:
                return AIMessage(content="Risk complete.")
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "calculate_position_size",
                        "args": {
                            "method": "kelly",
                            "win_rate": 0.55,
                            "avg_win": 0.02,
                            "avg_loss": 0.01,
                        },
                        "id": "risk-1",
                    }
                ],
            )
        if "Reporter" in system:
            return AIMessage(content="# Checkpoint smoke report\n\nOK.")
        return AIMessage(content="done")


def _sample_analysis_data() -> dict:
    dates = pd.bdate_range("2024-01-01", periods=30)
    df = pd.DataFrame(
        {
            "Open": range(100, 130),
            "High": range(101, 131),
            "Low": range(99, 129),
            "Close": range(100, 130),
            "Volume": [1_000_000] * 30,
        },
        index=dates,
    )
    df = add_daily_returns(df)
    return {"historical_data": df, "stock_info": {"symbol": "FIXTURE", "sector": "Tech"}}


def test_analysis_data_roundtrip_for_checkpoint():
    raw = _sample_analysis_data()
    packed = serialize_analysis_data(raw)
    restored = hydrate_analysis_data(packed)
    assert isinstance(restored["historical_data"], pd.DataFrame)
    assert len(restored["historical_data"]) == 30


def test_checkpoint_persists_thread_state(monkeypatch):
    monkeypatch.setenv("LANGGRAPH_CHECKPOINT", "memory")

    cp = MemorySaver()
    app = build_coordinator_graph(model=_MinimalFakeModel(), checkpointer=cp, enable_checkpoint=True)

    state = initial_state(
        case_id="cp_case",
        symbol="FIXTURE",
        task="checkpoint smoke",
        analysis_data=serialize_analysis_data(_sample_analysis_data()),
    )
    config = workflow_invoke_config("cp_case", thread_id="thread_cp_1")

    final = app.invoke(state, config=config)
    assert final.get("case_id") == "cp_case"

    snapshot = app.get_state(config)
    assert snapshot is not None
    assert snapshot.values.get("symbol") == "FIXTURE"
    assert snapshot.values.get("report")


def test_coordinator_get_thread_state(monkeypatch):
    monkeypatch.setenv("LANGGRAPH_CHECKPOINT", "memory")

    cp = MemorySaver()
    coordinator = AgentCoordinator(
        model=_MinimalFakeModel(),
        checkpointer=cp,
        enable_checkpoint=True,
    )
    packed = serialize_analysis_data(_sample_analysis_data())
    coordinator.run(
        case_id="coord_cp",
        symbol="FIXTURE",
        task="coordinator checkpoint",
        analysis_data=packed,
        thread_id="coord_thread_1",
    )

    saved = coordinator.get_thread_state("coord_cp", thread_id="coord_thread_1")
    assert saved is not None
    assert saved.get("symbol") == "FIXTURE"
    assert saved.get("report")


def test_sqlite_checkpointer_factory(monkeypatch):
    import shutil
    import uuid

    from quant_agent.agents.checkpoint import get_checkpointer, reset_checkpointer

    db_dir = Path(__file__).parent / "_checkpoint_tmp" / uuid.uuid4().hex
    db_dir.mkdir(parents=True, exist_ok=True)
    db_file = db_dir / "test.db"
    monkeypatch.setenv("LANGGRAPH_CHECKPOINT", "sqlite")
    monkeypatch.setenv("LANGGRAPH_CHECKPOINT_DB", str(db_file))

    reset_checkpointer()
    cp = get_checkpointer(force_new=True)
    assert cp is not None
    app = build_coordinator_graph(
        model=_MinimalFakeModel(),
        checkpointer=cp,
        enable_checkpoint=True,
    )
    state = initial_state(
        case_id="sqlite_cp",
        symbol="FIXTURE",
        task="sqlite checkpoint",
        analysis_data=serialize_analysis_data(_sample_analysis_data()),
    )
    config = workflow_invoke_config("sqlite_cp", thread_id="sqlite_t1")
    app.invoke(state, config=config)
    assert db_file.is_file()

    reset_checkpointer()
    shutil.rmtree(db_dir, ignore_errors=True)
