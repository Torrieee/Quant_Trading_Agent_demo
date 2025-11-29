from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import BacktestConfig


@dataclass
class BacktestResult:
    data: pd.DataFrame
    equity_curve_col: str
    stats: dict


def run_backtest(
    df: pd.DataFrame,
    signal_col: str,
    cfg: BacktestConfig,
    ret_col: str = "ret",
) -> BacktestResult:
    """
    非杠杆、单标的、全仓或空仓的简单多头回测：
    - 当 signal==1 时持有标的，仓位不超过 max_position
    - 手续费按换手 * fee_rate 扣减
    """
    df = df.copy()
    equity_col = "equity"

    # 仓位（0~max_position）
    position = df[signal_col].clip(lower=0, upper=1) * cfg.max_position
    position_prev = position.shift(1).fillna(0)

    # 换手率（绝对仓位变化）
    turnover = (position - position_prev).abs()

    gross_ret = position_prev * df[ret_col]
    fee = turnover * cfg.fee_rate
    net_ret = gross_ret - fee

    df["net_ret"] = net_ret
    df[equity_col] = (1 + net_ret).cumprod() * cfg.initial_cash

    # 计算简单统计指标
    equity = df[equity_col]
    daily_ret = df["net_ret"]

    total_ret = equity.iloc[-1] / equity.iloc[0] - 1 if len(equity) > 1 else 0.0
    ann_factor = 252
    ann_ret = (1 + total_ret) ** (ann_factor / len(df)) - 1 if len(df) > 0 else 0.0
    ann_vol = daily_ret.std() * np.sqrt(ann_factor)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0

    rolling_max = equity.cummax()
    drawdown = equity / rolling_max - 1
    max_dd = drawdown.min() if not drawdown.empty else 0.0

    stats = {
        "total_return": float(total_ret),
        "annual_return": float(ann_ret),
        "annual_volatility": float(ann_vol),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_dd),
        "num_days": int(len(df)),
    }

    return BacktestResult(data=df, equity_curve_col=equity_col, stats=stats)


__all__ = ["BacktestResult", "run_backtest"]



