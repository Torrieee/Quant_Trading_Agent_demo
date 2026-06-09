from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DataConfig(BaseModel):
    """数据相关配置。"""

    symbol: str = Field(..., description="标的代码，例如 AAPL、000001.SS 等")
    start: date = Field(..., description="开始日期")
    end: Optional[date] = Field(None, description="结束日期，默认为今天")
    interval: Literal["1d"] = Field("1d", description="K 线周期，目前示例仅支持日线")
    cache_dir: str = Field("data_cache", description="本地缓存目录")


class StrategyConfig(BaseModel):
    """策略参数配置。"""

    name: Literal["mean_reversion", "momentum"] = Field(
        "mean_reversion", description="策略名称"
    )

    # 均值回归参数
    mr_window: int = Field(20, ge=2, description="均值回归窗口长度")
    mr_threshold: float = Field(
        1.0, ge=0, description="均值回归 z-score 阈值，越大越保守"
    )

    # 动量策略参数
    mom_short_window: int = Field(20, ge=2, description="短周期均线窗口")
    mom_long_window: int = Field(60, ge=2, description="长周期均线窗口")


class BacktestConfig(BaseModel):
    """回测相关配置。"""

    initial_cash: float = Field(100_000, ge=0, description="初始资金")
    max_position: float = Field(
        1.0, ge=0, le=1.0, description="最大仓位（净资产比例）"
    )
    fee_rate: float = Field(0.0005, ge=0, description="单边手续费率")


class AgentConfig(BaseModel):
    """顶层 Agent 配置。"""

    data: DataConfig
    strategy: StrategyConfig = StrategyConfig()
    backtest: BacktestConfig = BacktestConfig()


__all__ = ["DataConfig", "StrategyConfig", "BacktestConfig", "AgentConfig"]



