import pandas as pd


def add_moving_averages(
    df: pd.DataFrame, windows: list[int], price_col: str = "Close"
) -> pd.DataFrame:
    """
    为收盘价添加多周期移动平均线。
    """
    for w in windows:
        df[f"ma_{w}"] = df[price_col].rolling(window=w, min_periods=w).mean()
    return df


def add_zscore(
    df: pd.DataFrame, window: int, price_col: str = "Close", col_name: str = "zscore"
) -> pd.DataFrame:
    """
    计算 rolling z-score，用于均值回归类策略。
    """
    rolling = df[price_col].rolling(window=window, min_periods=window)
    mean = rolling.mean()
    std = rolling.std(ddof=0)
    df[col_name] = (df[price_col] - mean) / std
    return df


def add_daily_returns(df: pd.DataFrame, price_col: str = "Close") -> pd.DataFrame:
    """
    计算日收益率。
    """
    df["ret"] = df[price_col].pct_change().fillna(0.0)
    return df


__all__ = ["add_moving_averages", "add_zscore", "add_daily_returns"]



