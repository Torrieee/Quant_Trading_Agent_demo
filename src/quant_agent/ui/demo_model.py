"""Demo mode: fake LLM + fixture data (no API key required)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from langchain_core.messages import AIMessage

from ..features import add_daily_returns

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures"


class DemoChatModel:
    """Minimal fake chat model for dashboard demo without DeepSeek API."""

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
                return AIMessage(content="研究完成。")
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_strategy_recommendation",
                        "args": {"market_state": "ranging"},
                        "id": "demo-r1",
                    }
                ],
            )
        if "Risk 智能体" in system:
            self._risk_calls += 1
            if self._risk_calls > 1:
                return AIMessage(content="风控完成。")
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
                        "id": "demo-k1",
                    }
                ],
            )
        if "Reporter" in system:
            return AIMessage(
                content=(
                    "# 投资分析报告（Demo）\n\n"
                    "## 摘要\n"
                    "基于分析面板的加权投票与工具链证据，当前环境偏震荡，建议均值回归策略。\n\n"
                    "## 证据\n"
                    "- 初步决策来自 Fundamental / Sentiment / Research 三 Agent 投票\n"
                    "- 策略推荐来自 `get_strategy_recommendation` 工具\n"
                    "- 仓位来自 Risk 智能体 `calculate_position_size`\n\n"
                    "## 风险提示\n"
                    "Demo 模式仅供界面演示，不构成投资建议。"
                )
            )
        return AIMessage(content="done")


def load_fixture_analysis_data(symbol: str, fixture_name: str = "sample_ohlcv.csv") -> dict:
    path = FIXTURES_DIR / fixture_name
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if "ret" not in df.columns:
        df = add_daily_returns(df)
    if "Adj Close" not in df.columns and "Close" in df.columns:
        df["Adj Close"] = df["Close"]
    return {
        "historical_data": df,
        "stock_info": {
            "symbol": symbol,
            "pe_ratio": 18.5,
            "pb_ratio": 2.8,
            "dividend_yield": 0.015,
            "sector": "Technology",
            "industry": "Consumer Electronics",
        },
    }
