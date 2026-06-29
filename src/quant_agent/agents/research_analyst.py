"""量化研究智能体（规则型信号，用于分析面板离线评估）。"""

from __future__ import annotations

from typing import Any

from ..market_state import MarketRegime, get_optimal_strategy_for_regime, identify_market_state
from .base import AgentSignal, BaseAgent


class ResearchAnalystAgent(BaseAgent):
    """基于市场状态识别与策略映射生成量化研究信号。"""

    def __init__(self) -> None:
        super().__init__(
            name="ResearchAnalyst",
            description="基于市场状态与策略匹配生成量化研究建议",
        )

    def analyze(self, symbol: str, data: dict[str, Any]) -> AgentSignal:
        if not self.validate_data(data, ["historical_data"]):
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=0,
                reasoning="缺少行情数据，无法完成量化研究分析",
            )

        df = data["historical_data"]
        if len(df) < 30:
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=30,
                reasoning="样本长度不足，量化研究结论可信度有限",
            )

        market_state = identify_market_state(df)
        strategy = get_optimal_strategy_for_regime(market_state)
        regime = market_state.regime

        if regime in (MarketRegime.TRENDING_UP, MarketRegime.LOW_VOLATILITY):
            signal_type = "buy"
            confidence = 55 + market_state.trend_strength * 35
            reasoning = (
                f"市场处于 {regime.value} 状态，趋势强度 {market_state.trend_strength:.2f}，"
                f"推荐策略 {strategy}"
            )
        elif regime in (MarketRegime.TRENDING_DOWN, MarketRegime.HIGH_VOLATILITY):
            signal_type = "sell"
            confidence = 55 + (1 - market_state.trend_strength) * 35
            reasoning = (
                f"市场处于 {regime.value} 状态，波动率 {market_state.volatility:.2%}，"
                f"建议谨慎并优先考虑 {strategy}"
            )
        else:
            signal_type = "hold"
            confidence = 50.0
            reasoning = (
                f"市场处于 {regime.value} 震荡区间，推荐策略 {strategy}，宜控制仓位"
            )

        current_price = float(df["Close"].iloc[-1])
        return AgentSignal(
            agent_name=self.name,
            signal_type=signal_type,
            confidence=round(min(95.0, confidence), 2),
            reasoning=reasoning,
            target_price=round(current_price * 1.08, 2) if signal_type == "buy" else None,
            stop_loss=round(current_price * 0.92, 2) if signal_type == "buy" else None,
            time_horizon="medium",
            metadata={
                "market_regime": regime.value,
                "recommended_strategy": strategy,
                "volatility": round(market_state.volatility, 4),
                "trend_strength": round(market_state.trend_strength, 4),
            },
        )
