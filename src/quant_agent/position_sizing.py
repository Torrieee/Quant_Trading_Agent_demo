"""
智能仓位管理模块

实现多种仓位管理方法：
1. 凯利公式（Kelly Criterion）
2. 风险平价（Risk Parity）
3. 固定分数（Fixed Fractional）
4. 波动率目标（Volatility Targeting）
"""

import numpy as np
import pandas as pd


def kelly_position_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    kelly_fraction: float = 0.25
) -> float:
    """
    凯利公式计算最优仓位
    
    凯利公式：f = (p * b - q) / b
    其中：
    - f: 最优仓位比例
    - p: 胜率
    - b: 盈亏比（平均盈利/平均亏损）
    - q: 败率 = 1 - p
    
    为了安全，通常使用凯利分数的1/4（Quarter Kelly）
    
    Parameters:
    -----------
    win_rate : float
        胜率（0-1）
    avg_win : float
        平均盈利（正数）
    avg_loss : float
        平均亏损（负数，取绝对值）
    kelly_fraction : float
        凯利分数比例（默认0.25，即使用1/4凯利）
    
    Returns:
    --------
    float
        建议仓位比例（0-1）
    """
    if avg_loss == 0 or win_rate <= 0:
        return 0.0
    
    p = win_rate
    q = 1 - p
    b = avg_win / abs(avg_loss)  # 盈亏比
    
    # 凯利公式
    kelly = (p * b - q) / b
    
    # 限制在合理范围内
    kelly = max(0.0, min(kelly, 0.5))  # 最多50%仓位
    
    # 使用部分凯利（更保守）
    return kelly * kelly_fraction


def risk_parity_position_size(
    volatility: float,
    target_volatility: float = 0.15,
    max_position: float = 1.0
) -> float:
    """
    风险平价仓位管理
    
    根据标的的波动率调整仓位，使组合风险保持在目标水平
    
    Parameters:
    -----------
    volatility : float
        标的的年化波动率
    target_volatility : float
        目标组合波动率（默认15%）
    max_position : float
        最大仓位限制
    
    Returns:
    --------
    float
        建议仓位比例（0-1）
    """
    if volatility <= 0:
        return 0.0
    
    # 风险平价：仓位 = 目标波动率 / 标的波动率
    position = target_volatility / volatility
    
    # 限制在合理范围内
    return min(position, max_position)


def volatility_targeting_position_size(
    returns: pd.Series,
    target_volatility: float = 0.15,
    lookback: int = 20,
    max_position: float = 1.0
) -> float:
    """
    波动率目标仓位管理
    
    根据历史波动率动态调整仓位，使组合波动率接近目标值
    
    Parameters:
    -----------
    returns : pd.Series
        历史收益率序列
    target_volatility : float
        目标年化波动率（默认15%）
    lookback : int
        回看窗口长度
    max_position : float
        最大仓位限制
    
    Returns:
    --------
    float
        建议仓位比例（0-1）
    """
    if len(returns) < lookback:
        return 0.0
    
    # 计算最近N天的年化波动率
    recent_returns = returns.tail(lookback)
    realized_vol = recent_returns.std() * np.sqrt(252)
    
    if realized_vol <= 0:
        return 0.0
    
    # 波动率目标：仓位 = 目标波动率 / 实现波动率
    position = target_volatility / realized_vol
    
    # 限制在合理范围内
    return min(position, max_position)


def fixed_fractional_position_size(
    equity: float,
    risk_per_trade: float = 0.02,
    stop_loss_pct: float = 0.05,
    max_position: float = 1.0
) -> float:
    """
    固定分数仓位管理
    
    每次交易只承担固定比例的账户风险
    
    Parameters:
    -----------
    equity : float
        当前账户权益
    risk_per_trade : float
        每笔交易的风险比例（默认2%）
    stop_loss_pct : float
        止损百分比（默认5%）
    max_position : float
        最大仓位限制
    
    Returns:
    --------
    float
        建议仓位比例（0-1）
    """
    if stop_loss_pct <= 0:
        return 0.0
    
    # 计算可以承受的损失金额
    risk_amount = equity * risk_per_trade
    
    # 根据止损百分比计算仓位
    # 如果止损5%，那么仓位 = 风险金额 / (价格 * 止损百分比)
    # 简化：假设当前价格为1，仓位 = 风险比例 / 止损比例
    position = risk_per_trade / stop_loss_pct
    
    # 限制在合理范围内
    return min(position, max_position)


def calculate_trade_statistics(
    equity_curve: pd.Series,
    signals: pd.Series
) -> dict:
    """
    计算交易统计信息，用于仓位管理
    
    Parameters:
    -----------
    equity_curve : pd.Series
        净值曲线
    signals : pd.Series
        交易信号（0或1）
    
    Returns:
    --------
    dict
        包含胜率、平均盈利、平均亏损等统计信息
    """
    # 计算收益率
    returns = equity_curve.pct_change()
    
    # 识别交易周期（信号从0变1为开仓，从1变0为平仓）
    position_changes = signals.diff()
    entry_points = position_changes[position_changes == 1].index
    exit_points = position_changes[position_changes == -1].index
    
    if len(entry_points) == 0:
        return {
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "num_trades": 0,
        }
    
    # 计算每笔交易的收益
    trade_returns = []
    for entry in entry_points:
        # 找到对应的平仓点
        exits_after = exit_points[exit_points > entry]
        if len(exits_after) > 0:
            exit = exits_after[0]
            # 计算持仓期间的累计收益
            period_returns = returns.loc[entry:exit]
            trade_return = (1 + period_returns).prod() - 1
            trade_returns.append(trade_return)
    
    if len(trade_returns) == 0:
        return {
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "num_trades": 0,
        }
    
    trade_returns = np.array(trade_returns)
    wins = trade_returns[trade_returns > 0]
    losses = trade_returns[trade_returns < 0]
    
    win_rate = len(wins) / len(trade_returns) if len(trade_returns) > 0 else 0.0
    avg_win = wins.mean() if len(wins) > 0 else 0.0
    avg_loss = abs(losses.mean()) if len(losses) > 0 else 0.0
    
    return {
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "num_trades": len(trade_returns),
    }


__all__ = [
    "kelly_position_size",
    "risk_parity_position_size",
    "volatility_targeting_position_size",
    "fixed_fractional_position_size",
    "calculate_trade_statistics",
]

