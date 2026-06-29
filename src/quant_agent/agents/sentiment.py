"""市场情绪分析智能体。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..core.analysis.sentiment import calculate_sentiment_indicators
from .base import AgentSignal, BaseAgent


class SentimentAgent(BaseAgent):
    """基于价格动量、成交量与波动率评估市场情绪。"""

    def __init__(self) -> None:
        super().__init__(
            name="SentimentAnalyst",
            description="基于市场情绪与动量生成交易信号",
        )

    def analyze(self, symbol: str, data: dict[str, Any]) -> AgentSignal:
        if not self.validate_data(data, ["historical_data"]):
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=0,
                reasoning="缺少历史行情，无法分析市场情绪",
            )

        df = data["historical_data"]
        if len(df) < 20:
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=30,
                reasoning="历史数据不足，无法判断市场情绪",
            )

        indicators = calculate_sentiment_indicators(df)
        sentiment_score = indicators["overall_sentiment"]
        momentum = indicators["momentum"]

        if sentiment_score > 70 and momentum > 0:
            signal_type = "buy"
            confidence = sentiment_score
            reasoning = _bullish_reason(indicators)
        elif sentiment_score < 30 and momentum < 0:
            signal_type = "sell"
            confidence = 100 - sentiment_score
            reasoning = _bearish_reason(indicators)
        else:
            signal_type = "hold"
            confidence = 50.0
            reasoning = _neutral_reason(indicators)

        current_price = float(df["Close"].iloc[-1])
        if signal_type == "buy":
            target_price = current_price * (1 + abs(momentum) / 100)
            stop_loss = current_price * 0.93
        elif signal_type == "sell":
            target_price = current_price * (1 - abs(momentum) / 100)
            stop_loss = current_price * 1.07
        else:
            target_price = None
            stop_loss = None

        return AgentSignal(
            agent_name=self.name,
            signal_type=signal_type,
            confidence=round(confidence, 2),
            reasoning=reasoning,
            target_price=round(target_price, 2) if target_price else None,
            stop_loss=round(stop_loss, 2) if stop_loss else None,
            time_horizon="medium",
            metadata={
                "sentiment_score": round(sentiment_score, 2),
                "momentum": round(momentum, 2),
                "volume_trend": indicators["volume_trend"],
                "volatility_state": indicators["volatility_state"],
            },
        )


def _bullish_reason(indicators: dict[str, Any]) -> str:
    lines = ["市场情绪积极，建议买入："]
    momentum = indicators.get("momentum", 0)
    lines.append(f"- 正向动量，近 10 日平均涨跌幅 {momentum:.2f}%")
    if indicators.get("volume_trend") == "high":
        lines.append("- 成交量放大，资金活跃度提升")
    return "\n".join(lines)


def _bearish_reason(indicators: dict[str, Any]) -> str:
    lines = ["市场情绪偏弱，建议卖出："]
    momentum = indicators.get("momentum", 0)
    lines.append(f"- 负向动量，近 10 日平均涨跌幅 {momentum:.2f}%")
    if indicators.get("volume_trend") == "high":
        lines.append("- 放量下跌，抛压较重")
    return "\n".join(lines)


def _neutral_reason(indicators: dict[str, Any]) -> str:
    sentiment = indicators.get("overall_sentiment", 50)
    lines = [f"市场情绪中性（综合评分 {sentiment:.1f}/100），建议观望"]
    if indicators.get("volatility_state") == "high":
        lines.append("- 波动率偏高，不确定性较大")
    return "\n".join(lines)
