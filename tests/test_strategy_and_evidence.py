"""策略推荐与 Evidence 层单元测试。"""

from __future__ import annotations

from quant_agent.evidence import EvidenceRetriever
from quant_agent.llm_agent import TradingFunctionCaller
from quant_agent.strategy_recommendation import recommend_strategy


def test_recommend_strategy_ranging_prefers_mean_reversion():
    result = recommend_strategy(symbol="TEST", market_state="ranging")
    assert "error" not in result
    assert result["recommended_strategy"] in ("momentum", "mean_reversion")
    assert "scores" in result
    assert "confidence" in result
    assert "alternatives" in result
    assert result["scores"]["mean_reversion"] >= result["scores"]["momentum"]


def test_recommend_strategy_trending_up_with_real_metrics():
    result = recommend_strategy(
        symbol="AAPL",
        market_state="trending_up",
        volatility=0.15,
        trend_strength=0.85,
        is_bullish=True,
        is_bearish=False,
    )
    assert result["recommended_strategy"] == "momentum"
    assert result["inputs_used"]["source"] == "arguments"


def test_recommend_strategy_respects_risk_flags():
    base = recommend_strategy(symbol="X", market_state="trending_up", trend_strength=0.8)
    risky = recommend_strategy(
        symbol="X",
        market_state="trending_up",
        trend_strength=0.8,
        risk_flags=["going_concern"],
    )
    assert risky["confidence"] <= base["confidence"]


def test_evidence_fixture_has_supply_chain_flag():
    retriever = EvidenceRetriever()
    retriever.ensure_index("FIXTURE", stock_info={"symbol": "FIXTURE", "sector": "Tech"})
    snapshot = retriever.get_snapshot("FIXTURE", "supply chain risk analysis")
    assert snapshot
    fields = retriever.snapshot_to_state(snapshot, symbol="FIXTURE")
    assert "supply_chain" in fields.get("risk_flags", [])


def test_search_evidence_tool():
    caller = TradingFunctionCaller(evidence_retriever=EvidenceRetriever())
    caller.evidence_retriever.ensure_index("FIXTURE")
    out = caller.call_function(
        "search_evidence",
        {"symbol": "FIXTURE", "query": "supply chain", "top_k": 3},
    )
    assert out["count"] >= 1
    assert out["retrieved_documents"]


def test_get_strategy_recommendation_tool_backward_compat():
    caller = TradingFunctionCaller()
    out = caller.call_function("get_strategy_recommendation", {"market_state": "ranging"})
    assert out["recommended_strategy"] in ("momentum", "mean_reversion")
    assert "reason" in out
    assert "scores" in out
