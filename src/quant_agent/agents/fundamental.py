"""基本面分析智能体。"""

from __future__ import annotations

from typing import Any

from ..core.analysis.fundamental import FundamentalAnalyzer
from .base import AgentSignal, BaseAgent


class FundamentalAgent(BaseAgent):
    """基于估值与成长性指标生成中长期投资建议。"""

    def __init__(self) -> None:
        super().__init__(
            name="FundamentalAnalyst",
            description="基于基本面分析生成中长期投资建议",
        )
        self.analyzer = FundamentalAnalyzer()

    def analyze(self, symbol: str, data: dict[str, Any]) -> AgentSignal:
        if not self.validate_data(data, ["stock_info", "historical_data"]):
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=0,
                reasoning="缺少基本面数据，无法进行分析",
            )

        stock_info = data["stock_info"]
        historical_data = data["historical_data"]
        analysis = self.analyzer.full_fundamental_analysis(stock_info, historical_data)

        valuation = analysis["valuation"]
        growth = analysis["growth"]
        overall_score = analysis["overall_score"]

        if overall_score >= 70:
            signal_type = "buy"
            confidence = min(95.0, overall_score)
            reasoning = _buy_reason(valuation, growth)
        elif overall_score <= 30:
            signal_type = "sell"
            confidence = min(95.0, 100.0 - overall_score)
            reasoning = _sell_reason(valuation, growth)
        else:
            signal_type = "hold"
            confidence = 50.0
            reasoning = _hold_reason(valuation, growth)

        current_price = float(historical_data["Close"].iloc[-1])
        target_price, stop_loss = _price_targets(signal_type, current_price, valuation)

        return AgentSignal(
            agent_name=self.name,
            signal_type=signal_type,
            confidence=round(confidence, 2),
            reasoning=reasoning,
            target_price=target_price,
            stop_loss=stop_loss,
            time_horizon="long",
            metadata={
                "valuation_score": round(valuation["valuation_score"], 2),
                "growth_score": round(growth["growth_score"], 2),
                "overall_score": round(overall_score, 2),
                "pe_ratio": valuation.get("pe_ratio", 0),
                "pb_ratio": valuation.get("pb_ratio", 0),
                "trend": growth.get("trend", "unknown"),
            },
        )


def _price_targets(
    signal_type: str,
    current_price: float,
    valuation: dict[str, Any],
) -> tuple[float | None, float | None]:
    if signal_type == "buy":
        pe = valuation.get("pe_ratio") or 0
        if 0 < pe < 50:
            target = current_price * (25.0 / pe)
        else:
            target = current_price * 1.15
        return round(target, 2), round(current_price * 0.90, 2)
    if signal_type == "sell":
        return round(current_price * 0.85, 2), round(current_price * 1.10, 2)
    return None, None


def _buy_reason(valuation: dict[str, Any], growth: dict[str, Any]) -> str:
    lines = ["基本面综合评分优秀，建议买入："]
    pe = valuation.get("pe_ratio") or 100
    if pe < 20:
        lines.append(f"- PE 估值合理（{pe:.2f}），具备一定安全边际")
    pb = valuation.get("pb_ratio") or 100
    if pb < 3:
        lines.append(f"- PB 估值较低（{pb:.2f}）")
    if growth.get("trend") in ("uptrend", "strong_uptrend"):
        lines.append(f"- 价格趋势向上，近三月涨幅 {growth.get('return_3m', 0):.2f}%")
    return "\n".join(lines)


def _sell_reason(valuation: dict[str, Any], growth: dict[str, Any]) -> str:
    lines = ["基本面综合评分偏弱，建议卖出或规避："]
    pe = valuation.get("pe_ratio") or 0
    if pe > 50:
        lines.append(f"- PE 估值偏高（{pe:.2f}）")
    if growth.get("trend") in ("downtrend", "strong_downtrend"):
        lines.append(f"- 价格趋势向下，近三月跌幅 {abs(growth.get('return_3m', 0)):.2f}%")
    return "\n".join(lines)


def _hold_reason(valuation: dict[str, Any], growth: dict[str, Any]) -> str:
    lines = ["基本面评分中性，建议观望："]
    pe = valuation.get("pe_ratio") or 0
    if 20 <= pe <= 40:
        lines.append(f"- PE 估值适中（{pe:.2f}）")
    if growth.get("trend") == "sideways":
        lines.append("- 价格处于横盘整理阶段")
    return "\n".join(lines)
