"""
市场状态识别模块

识别当前市场状态（趋势市、震荡市、牛市、熊市等），
为策略选择提供依据。
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd


class MarketRegime(Enum):
    """市场状态枚举"""
    TRENDING_UP = "trending_up"  # 上升趋势
    TRENDING_DOWN = "trending_down"  # 下降趋势
    RANGING = "ranging"  # 震荡
    HIGH_VOLATILITY = "high_volatility"  # 高波动
    LOW_VOLATILITY = "low_volatility"  # 低波动


@dataclass
class MarketState:
    """市场状态数据类"""
    regime: MarketRegime
    volatility: float  # 波动率
    trend_strength: float  # 趋势强度 (0-1)
    adx: float  # ADX指标
    atr: float  # ATR指标
    bollinger_width: float  # 布林带宽度
    is_bullish: bool  # 是否看涨
    is_bearish: bool  # 是否看跌


def calculate_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """
    计算平均真实波幅（ATR）
    
    ATR用于衡量市场波动性
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean()
    
    return atr


def calculate_adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """
    计算平均趋向指标（ADX）
    
    ADX用于衡量趋势强度，不区分方向
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    
    # 计算+DM和-DM
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # 计算TR
    tr = calculate_atr(df, window=1)
    
    # 计算+DI和-DI
    plus_di = 100 * (plus_dm.rolling(window=window).mean() / tr.rolling(window=window).mean())
    minus_di = 100 * (minus_dm.rolling(window=window).mean() / tr.rolling(window=window).mean())
    
    # 计算DX
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    
    # 计算ADX
    adx = dx.rolling(window=window).mean()
    
    return adx


def calculate_bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: float = 2.0):
    """
    计算布林带
    
    返回上轨、中轨、下轨和带宽
    """
    close = df["Close"]
    ma = close.rolling(window=window).mean()
    std = close.rolling(window=window).std()
    
    upper = ma + (std * num_std)
    lower = ma - (std * num_std)
    width = (upper - lower) / ma  # 相对宽度
    
    return upper, ma, lower, width


def identify_market_state(df: pd.DataFrame, lookback: int = 20) -> MarketState:
    """
    识别当前市场状态
    
    Parameters:
    -----------
    df : pd.DataFrame
        包含OHLCV数据的DataFrame
    lookback : int
        回看窗口长度
    
    Returns:
    --------
    MarketState
        当前市场状态
    """
    df = df.copy()
    
    # 计算技术指标
    atr = calculate_atr(df, window=14)
    adx = calculate_adx(df, window=14)
    _, _, _, bollinger_width = calculate_bollinger_bands(df, window=20)
    
    # 获取最新值
    current_atr = atr.iloc[-1]
    current_adx = adx.iloc[-1]
    current_bb_width = bollinger_width.iloc[-1]
    
    # 计算历史波动率（最近N天的收益率标准差）
    returns = df["Close"].pct_change()
    volatility = returns.tail(lookback).std() * np.sqrt(252)  # 年化波动率
    
    # 判断趋势方向
    ma_short = df["Close"].rolling(window=20).mean().iloc[-1]
    ma_long = df["Close"].rolling(window=60).mean().iloc[-1]
    current_price = df["Close"].iloc[-1]
    
    is_bullish = (ma_short > ma_long) and (current_price > ma_short)
    is_bearish = (ma_short < ma_long) and (current_price < ma_short)
    
    # 趋势强度（ADX归一化，一般认为ADX>25表示强趋势）
    trend_strength = min(current_adx / 25.0, 1.0) if not pd.isna(current_adx) else 0.0
    
    # 判断市场状态
    if trend_strength > 0.5:  # 强趋势
        if is_bullish:
            regime = MarketRegime.TRENDING_UP
        elif is_bearish:
            regime = MarketRegime.TRENDING_DOWN
        else:
            regime = MarketRegime.RANGING
    else:  # 弱趋势，可能是震荡
        if volatility > 0.3:  # 高波动率阈值
            regime = MarketRegime.HIGH_VOLATILITY
        else:
            regime = MarketRegime.LOW_VOLATILITY
    
    return MarketState(
        regime=regime,
        volatility=volatility,
        trend_strength=trend_strength,
        adx=current_adx if not pd.isna(current_adx) else 0.0,
        atr=current_atr if not pd.isna(current_atr) else 0.0,
        bollinger_width=current_bb_width if not pd.isna(current_bb_width) else 0.0,
        is_bullish=is_bullish,
        is_bearish=is_bearish,
    )


def get_optimal_strategy_for_regime(market_state: MarketState) -> str:
    """
    根据市场状态推荐最优策略
    
    Returns:
    --------
    str
        推荐策略名称
    """
    if market_state.regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
        # 趋势市适合动量策略
        return "momentum"
    elif market_state.regime == MarketRegime.RANGING:
        # 震荡市适合均值回归策略
        return "mean_reversion"
    elif market_state.regime == MarketRegime.HIGH_VOLATILITY:
        # 高波动时，均值回归可能更安全
        return "mean_reversion"
    else:
        # 低波动时，可以尝试动量策略
        return "momentum"


__all__ = [
    "MarketRegime",
    "MarketState",
    "calculate_atr",
    "calculate_adx",
    "calculate_bollinger_bands",
    "identify_market_state",
    "get_optimal_strategy_for_regime",
]

