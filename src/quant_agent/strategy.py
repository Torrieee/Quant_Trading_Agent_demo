from dataclasses import dataclass

import pandas as pd

from .config import StrategyConfig
from .features import add_daily_returns, add_moving_averages, add_zscore


@dataclass
class StrategyResult:
    data: pd.DataFrame
    signal_col: str


def prepare_features(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """
    根据策略配置，给原始 K 线数据添加所需特征。
    """
    df = df.copy()
    df = add_daily_returns(df)
    df = add_moving_averages(
        df, [cfg.mr_window, cfg.mom_short_window, cfg.mom_long_window]
    )
    df = add_zscore(df, window=cfg.mr_window, price_col="Close", col_name="zscore")
    return df


def mean_reversion_signals(df: pd.DataFrame, cfg: StrategyConfig) -> StrategyResult:
    """
    简单均值回归策略：
    - zscore < -threshold 时做多
    - zscore > threshold 时平仓（或做空，这里示例用平仓）
    """
    df = df.copy()
    signal_col = "signal_mr"

    df[signal_col] = 0
    df.loc[df["zscore"] < -cfg.mr_threshold, signal_col] = 1
    df.loc[df["zscore"] > cfg.mr_threshold, signal_col] = 0

    df[signal_col] = df[signal_col].ffill().fillna(0)
    return StrategyResult(data=df, signal_col=signal_col)


def momentum_signals(df: pd.DataFrame, cfg: StrategyConfig) -> StrategyResult:
    """
    简单动量策略：
    - 短周期均线向上突破长周期均线时做多
    - 短周期均线向下跌破长周期均线时平仓
    """
    df = df.copy()
    signal_col = "signal_mom"

    short_col = f"ma_{cfg.mom_short_window}"
    long_col = f"ma_{cfg.mom_long_window}"

    df["ma_diff"] = df[short_col] - df[long_col]
    df["ma_diff_prev"] = df["ma_diff"].shift(1)

    df[signal_col] = 0
    # 上穿：前一日 diff <= 0 且当日 diff > 0
    buy_mask = (df["ma_diff_prev"] <= 0) & (df["ma_diff"] > 0)
    df.loc[buy_mask, signal_col] = 1

    # 下穿：前一日 diff >= 0 且当日 diff < 0
    sell_mask = (df["ma_diff_prev"] >= 0) & (df["ma_diff"] < 0)
    df.loc[sell_mask, signal_col] = 0

    df[signal_col] = df[signal_col].ffill().fillna(0)
    return StrategyResult(data=df, signal_col=signal_col)


def build_strategy(df: pd.DataFrame, cfg: StrategyConfig) -> StrategyResult:
    """
    对外暴露的策略构建入口，根据 name 选择具体策略。
    """
    df_feat = prepare_features(df, cfg)

    if cfg.name == "mean_reversion":
        return mean_reversion_signals(df_feat, cfg)
    if cfg.name == "momentum":
        return momentum_signals(df_feat, cfg)

    raise ValueError(f"Unknown strategy name: {cfg.name}")


__all__ = ["StrategyResult", "prepare_features", "build_strategy"]



