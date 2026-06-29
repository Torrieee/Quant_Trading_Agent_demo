"""基本面分析器：估值、成长性与综合评分。"""

from __future__ import annotations

from typing import Any

import pandas as pd


class FundamentalAnalyzer:
    """基于财务估值与价格趋势的基本面分析。"""

    def full_fundamental_analysis(
        self,
        stock_info: dict[str, Any],
        historical_data: pd.DataFrame,
    ) -> dict[str, Any]:
        valuation = self._analyze_valuation(stock_info)
        growth = self._analyze_growth(historical_data)
        overall_score = (valuation["valuation_score"] + growth["growth_score"]) / 2.0
        return {
            "valuation": valuation,
            "growth": growth,
            "overall_score": overall_score,
        }

    def _analyze_valuation(self, stock_info: dict[str, Any]) -> dict[str, Any]:
        pe = _safe_float(stock_info.get("pe_ratio"))
        pb = _safe_float(stock_info.get("pb_ratio"))
        dividend_yield = _safe_float(stock_info.get("dividend_yield"))

        score = 50.0
        if pe is not None:
            if 0 < pe < 15:
                score += 20
            elif 15 <= pe < 25:
                score += 10
            elif pe >= 50:
                score -= 25
            elif pe >= 35:
                score -= 15

        if pb is not None:
            if 0 < pb < 2:
                score += 15
            elif 2 <= pb < 4:
                score += 5
            elif pb >= 10:
                score -= 20

        if dividend_yield is not None and dividend_yield > 0.02:
            score += 10

        score = max(0.0, min(100.0, score))
        return {
            "valuation_score": score,
            "pe_ratio": pe or 0.0,
            "pb_ratio": pb or 0.0,
            "dividend_yield": dividend_yield or 0.0,
        }

    def _analyze_growth(self, historical_data: pd.DataFrame) -> dict[str, Any]:
        df = historical_data
        if len(df) < 20:
            return {
                "growth_score": 50.0,
                "return_3m": 0.0,
                "trend": "unknown",
            }

        close = df["Close"]
        return_3m = 0.0
        if len(df) >= 60:
            return_3m = (close.iloc[-1] - close.iloc[-60]) / close.iloc[-60] * 100
        elif len(df) >= 20:
            return_3m = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] * 100

        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(min(60, len(close))).mean().iloc[-1]
        current = close.iloc[-1]

        if current > ma20 > ma60:
            trend = "strong_uptrend"
        elif current > ma20:
            trend = "uptrend"
        elif current < ma20 < ma60:
            trend = "strong_downtrend"
        elif current < ma20:
            trend = "downtrend"
        else:
            trend = "sideways"

        score = 50.0
        if return_3m > 10:
            score += 25
        elif return_3m > 3:
            score += 15
        elif return_3m < -10:
            score -= 25
        elif return_3m < -3:
            score -= 15

        if trend in ("uptrend", "strong_uptrend"):
            score += 10
        elif trend in ("downtrend", "strong_downtrend"):
            score -= 10

        score = max(0.0, min(100.0, score))
        return {
            "growth_score": score,
            "return_3m": return_3m,
            "trend": trend,
        }


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None
