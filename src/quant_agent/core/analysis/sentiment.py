"""市场情绪指标计算。"""

from __future__ import annotations

from typing import Any

import pandas as pd


def calculate_sentiment_indicators(df: pd.DataFrame) -> dict[str, Any]:
    """根据价格动量、成交量与波动率计算综合情绪评分（0-100）。"""
    returns_5d = (df["Close"].iloc[-1] - df["Close"].iloc[-5]) / df["Close"].iloc[-5] * 100
    returns_10d = (df["Close"].iloc[-1] - df["Close"].iloc[-10]) / df["Close"].iloc[-10] * 100
    momentum = (returns_5d + returns_10d) / 2

    vol_ma5 = df["Volume"].iloc[-5:].mean()
    vol_ma20 = df["Volume"].iloc[-20:].mean()
    volume_ratio = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1.0

    if volume_ratio > 1.3:
        volume_trend = "high"
    elif volume_ratio < 0.7:
        volume_trend = "low"
    else:
        volume_trend = "normal"

    volatility = df["Close"].pct_change().std() * 100
    if volatility > 3:
        volatility_state = "high"
    elif volatility < 1:
        volatility_state = "low"
    else:
        volatility_state = "normal"

    momentum_score = max(0.0, min(100.0, 50 + momentum * 2))

    if volume_trend == "high":
        volume_score = 70 if momentum > 0 else 30
    elif volume_trend == "low":
        volume_score = 40
    else:
        volume_score = 50

    if volatility_state == "high":
        volatility_score = 40
    elif volatility_state == "low":
        volatility_score = 60
    else:
        volatility_score = 50

    overall_sentiment = (
        momentum_score * 0.4 + volume_score * 0.3 + volatility_score * 0.3
    )

    return {
        "momentum": momentum,
        "returns_5d": returns_5d,
        "returns_10d": returns_10d,
        "volume_ratio": volume_ratio,
        "volume_trend": volume_trend,
        "volatility": volatility,
        "volatility_state": volatility_state,
        "momentum_score": momentum_score,
        "volume_score": volume_score,
        "volatility_score": volatility_score,
        "overall_sentiment": overall_sentiment,
    }
