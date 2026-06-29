"""Research 动态子图单元测试。"""

from __future__ import annotations

from quant_agent.agents.state import initial_state
from quant_agent.agents.subgraphs.planner import build_research_plan
from quant_agent.agents.subgraphs.verifier import verify_research
from quant_agent.runtime.tool_adapter import HarnessToolAdapter


def test_planner_adds_evidence_for_supply_chain_task():
    state = initial_state(case_id="t", symbol="FIXTURE", task="评估供应链与亚洲制造风险")
    state["quant_state"] = {"risk_flags": ["supply_chain"]}
    plan = build_research_plan(state)
    workers = [p["worker"] for p in plan]
    assert "evidence" in workers
    assert "strategy" in workers


def test_verifier_passes_with_strategy_and_evidence():
    state = {
        "research_plan": [
            {"worker": "evidence", "required_evidence": True},
            {"worker": "strategy", "required_evidence": False},
        ],
        "research_findings": [
            {"worker": "evidence", "status": "ok", "evidence_ids": ["FIXTURE_10-K_0"]},
            {"worker": "strategy", "status": "ok", "evidence_ids": []},
        ],
        "quant_state": {"recommended_strategy": "mean_reversion", "risk_flags": ["supply_chain"]},
    }
    ver = verify_research(state)
    assert ver["passed"] is True


def test_dynamic_research_e2e_offline():
    from quant_agent.agents.subgraphs import run_dynamic_research

    state = initial_state(
        case_id="dyn",
        symbol="FIXTURE",
        task="评估 FIXTURE 供应链风险并推荐策略",
        gate={"max_steps": 16},
    )
    state["workflow_flags"] = {"enable_dynamic_research": True}
    state["quant_state"] = {
        "risk_flags": ["supply_chain"],
        "symbol": "FIXTURE",
        "market_regime": "ranging",
        "recommended_strategy": "mean_reversion",
    }
    state["analysis_complete"] = True
    state["retrieval_complete"] = True

    adapter = HarnessToolAdapter()
    out = run_dynamic_research(state, adapter)
    assert out.get("research_complete") is True
    qs = out.get("quant_state") or {}
    assert qs.get("recommended_strategy")
    assert len(qs.get("research_findings") or []) >= 2
    agents = [s.get("agent") for s in out.get("trace_steps") or []]
    assert "research_workers_join" in agents
    assert any(s.get("parallel") for s in out.get("trace_steps") or [])


def test_parallel_worker_dispatch_in_plan():
    state = initial_state(case_id="t", symbol="FIXTURE", task="评估供应链风险")
    state["quant_state"] = {"risk_flags": ["supply_chain"]}
    plan = build_research_plan(state)
    parallel = [p["worker"] for p in plan if p.get("worker") in ("evidence", "market")]
    assert len(parallel) >= 2
