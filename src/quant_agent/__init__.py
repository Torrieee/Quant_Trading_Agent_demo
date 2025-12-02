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
- market_state: 市场状态识别模块
- position_sizing: 智能仓位管理模块
- rl_env: 强化学习交易环境（Gym接口）
- rl_trainer: 强化学习训练模块
- llm_agent: 大模型Agent集成模块（Function Calling、RAG）
- llm_strategy: LLM驱动的策略生成和解释模块（原创功能）
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
    "market_state",
    "position_sizing",
    "rl_env",
    "rl_trainer",
    "llm_agent",
    "llm_strategy",
]


