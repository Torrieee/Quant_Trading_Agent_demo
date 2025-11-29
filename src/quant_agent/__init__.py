"""
Quant Trading Agent package.

核心模块包括：
- config: 配置模型
- data: 数据下载与缓存
- features: 技术指标与特征工程
- strategy: 策略定义与信号生成
- backtester: 回测引擎
- agent: TradingAgent 类 - 智能交易 Agent，负责感知、决策、执行、评估
- optimizer: 自动参数优化模块
"""

from .agent import TradingAgent, AgentRunResult, run_agent
from .config import AgentConfig, BacktestConfig, DataConfig, StrategyConfig

__all__ = [
    "TradingAgent",
    "AgentRunResult",
    "run_agent",
    "AgentConfig",
    "BacktestConfig",
    "DataConfig",
    "StrategyConfig",
    "config",
    "data",
    "features",
    "strategy",
    "backtester",
    "agent",
    "optimizer",
]


