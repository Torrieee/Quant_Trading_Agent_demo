from dataclasses import dataclass
from typing import Optional

from loguru import logger

from .backtester import BacktestResult, run_backtest
from .config import AgentConfig
from .data import download_ohlcv
from .strategy import StrategyResult, build_strategy


@dataclass
class AgentRunResult:
    """Agent 运行结果，包含配置、策略结果和回测结果。"""
    config: AgentConfig
    strategy_result: StrategyResult
    backtest_result: BacktestResult


class TradingAgent:
    """
    量化交易 Agent 类。
    
    Agent 负责：
    1. 感知环境（获取市场数据）
    2. 决策（选择策略和参数）
    3. 执行（运行回测）
    4. 评估（分析结果并优化）
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.data: Optional = None
        self.strategy_result: Optional[StrategyResult] = None
        self.backtest_result: Optional[BacktestResult] = None
    
    def perceive(self):
        """
        Agent 感知环境：获取市场数据。
        """
        logger.info(f"Agent: Perceiving market data for {self.config.data.symbol}")
        self.data = download_ohlcv(self.config.data)
        logger.info(f"Agent: Loaded data shape: {self.data.shape}")
        return self.data
    
    def decide(self):
        """
        Agent 决策：根据配置和当前数据选择策略并生成交易信号。
        """
        if self.data is None:
            raise ValueError("Agent must perceive (load data) before deciding")
        
        logger.info(f"Agent: Deciding strategy - {self.config.strategy.name}")
        self.strategy_result = build_strategy(self.data, self.config.strategy)
        logger.info(f"Agent: Strategy built, signal_col={self.strategy_result.signal_col}")
        return self.strategy_result
    
    def act(self):
        """
        Agent 执行：运行回测，模拟交易执行。
        """
        if self.strategy_result is None:
            raise ValueError("Agent must decide (build strategy) before acting")
        
        logger.info("Agent: Acting - running backtest")
        self.backtest_result = run_backtest(
            self.strategy_result.data,
            signal_col=self.strategy_result.signal_col,
            cfg=self.config.backtest,
            ret_col="ret",
        )
        logger.info("Agent: Backtest finished")
        return self.backtest_result
    
    def evaluate(self) -> dict:
        """
        Agent 评估：分析回测结果，返回关键指标。
        """
        if self.backtest_result is None:
            raise ValueError("Agent must act (run backtest) before evaluating")
        
        stats = self.backtest_result.stats
        logger.info(f"Agent: Evaluation - Stats: {stats}")
        return stats
    
    def run(self) -> AgentRunResult:
        """
        Agent 完整运行流程：感知 -> 决策 -> 执行 -> 评估。
        
        这是 Agent 的主要入口方法，体现了 Agent 的自主决策能力。
        """
        logger.info("=" * 50)
        logger.info("Agent: Starting complete workflow")
        logger.info("=" * 50)
        
        # 1. 感知环境
        self.perceive()
        
        # 2. 决策
        self.decide()
        
        # 3. 执行
        self.act()
        
        # 4. 评估
        self.evaluate()
        
        logger.info("=" * 50)
        logger.info("Agent: Workflow completed")
        logger.info("=" * 50)
        
        return AgentRunResult(
            config=self.config,
            strategy_result=self.strategy_result,
            backtest_result=self.backtest_result,
        )


def run_agent(cfg: AgentConfig) -> AgentRunResult:
    """
    便捷函数：创建并运行 Agent。
    
    这是向后兼容的接口，内部使用 TradingAgent 类。
    """
    agent = TradingAgent(cfg)
    return agent.run()


__all__ = ["AgentRunResult", "run_agent"]


