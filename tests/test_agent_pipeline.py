"""TradingAgent pipeline tests."""

import pytest

from quant_agent.agent import TradingAgent


def test_agent_pipeline_run(mock_download_ohlcv, agent_config):
    agent = TradingAgent(agent_config)
    result = agent.run()

    assert result.strategy_result is not None
    assert result.backtest_result is not None
    assert result.backtest_result.stats
    assert agent.data is not None
    assert agent.strategy_result is not None
    assert agent.backtest_result is not None


def test_agent_decide_without_perceive_raises(agent_config):
    agent = TradingAgent(agent_config)
    with pytest.raises(ValueError, match="perceive"):
        agent.decide()


def test_agent_act_without_decide_raises(mock_download_ohlcv, agent_config):
    agent = TradingAgent(agent_config)
    agent.perceive()
    with pytest.raises(ValueError, match="decide"):
        agent.act()
