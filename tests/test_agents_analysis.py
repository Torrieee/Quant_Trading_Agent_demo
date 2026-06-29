"""QuantEngine 与分析智能体单元测试。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from langchain_core.messages import AIMessage

from quant_agent.agents.fundamental import FundamentalAgent
from quant_agent.agents.research_analyst import ResearchAnalystAgent
from quant_agent.agents.sentiment import SentimentAgent
from quant_agent.agents.signal_aggregate import aggregate_signals
from quant_agent.engine import QuantEngine
from quant_agent.features import add_daily_returns

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_ohlcv.csv"


class _FakeApiModel:
    """模拟 DeepSeek API，供单元测试注入。"""

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
                return AIMessage(content="done")
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_strategy_recommendation",
                        "args": {"market_state": "ranging"},
                        "id": "r1",
                    }
                ],
            )
        if "Risk 智能体" in system:
            self._risk_calls += 1
            if self._risk_calls > 1:
                return AIMessage(content="done")
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
                        "id": "k1",
                    }
                ],
            )
        if "Reporter" in system:
            return AIMessage(content="# 报告\n\n测试报告内容。")
        return AIMessage(content="done")


@pytest.fixture
def analysis_data() -> dict:
    df = pd.read_csv(FIXTURE, index_col=0, parse_dates=True)
    if "ret" not in df.columns:
        df = add_daily_returns(df)
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]
    return {
        "historical_data": df,
        "stock_info": {
            "symbol": "FIXTURE",
            "pe_ratio": 16.0,
            "pb_ratio": 2.5,
            "dividend_yield": 0.02,
        },
    }


def test_fundamental_agent_returns_signal(analysis_data):
    sig = FundamentalAgent().analyze("FIXTURE", analysis_data)
    assert sig.agent_name == "FundamentalAnalyst"
    assert sig.signal_type in ("buy", "sell", "hold")
    assert 0 <= sig.confidence <= 100


def test_sentiment_agent_returns_signal(analysis_data):
    sig = SentimentAgent().analyze("FIXTURE", analysis_data)
    assert sig.agent_name == "SentimentAnalyst"
    assert sig.signal_type in ("buy", "sell", "hold")


def test_research_analyst_returns_strategy(analysis_data):
    sig = ResearchAnalystAgent().analyze("FIXTURE", analysis_data)
    assert sig.agent_name == "ResearchAnalyst"
    assert "recommended_strategy" in sig.metadata


def test_aggregate_signals_weighted():
    from quant_agent.agents.base import AgentSignal

    signals = {
        "FundamentalAnalyst": AgentSignal(
            agent_name="FundamentalAnalyst",
            signal_type="buy",
            confidence=80,
            reasoning="r",
        ),
        "SentimentAnalyst": AgentSignal(
            agent_name="SentimentAnalyst",
            signal_type="hold",
            confidence=50,
            reasoning="r",
        ),
        "ResearchAnalyst": AgentSignal(
            agent_name="ResearchAnalyst",
            signal_type="buy",
            confidence=70,
            reasoning="r",
        ),
    }
    decision = aggregate_signals(signals)
    assert decision["signal_type"] in ("buy", "hold", "sell")
    assert "scores" in decision


def test_quant_engine_with_injected_model(analysis_data):
    result = QuantEngine(model=_FakeApiModel()).analyze(
        "FIXTURE",
        task="API 工作流测试",
        analysis_data=analysis_data,
        gate={"max_steps": 12},
    )
    assert result.decision
    assert result.risk_verdict == "pass"
    assert result.report
    assert "research" in result.agents_visited
    assert "document_retrieval" in result.agents_visited
    assert "reporter" in result.agents_visited


def test_quant_engine_requires_api_key_without_model(monkeypatch, analysis_data):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    result = QuantEngine(model=None).analyze(
        "FIXTURE",
        analysis_data=analysis_data,
    )
    assert not result.success
    assert result.error
    assert "DEEPSEEK_API_KEY" in result.error
