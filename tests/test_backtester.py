"""Backtester structural tests."""

import numpy as np
import pandas as pd

from quant_agent.backtester import run_backtest
from quant_agent.config import BacktestConfig


def _make_df(signal_values: list[int], n: int | None = None) -> pd.DataFrame:
    n = n or len(signal_values)
    dates = pd.bdate_range("2020-01-01", periods=n)
    close = np.linspace(100, 110, n)
    df = pd.DataFrame(
        {
            "Open": close,
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
            "Volume": 1_000_000,
            "ret": np.concatenate([[0.0], np.diff(close) / close[:-1]]),
            "signal": signal_values,
        },
        index=dates,
    )
    return df


def test_backtester_stats_fields(sample_ohlcv):
    df = sample_ohlcv.copy()
    df["signal"] = (df["Close"] > df["Close"].rolling(5).mean()).astype(int)

    result = run_backtest(df, "signal", BacktestConfig())
    stats = result.stats

    for key in (
        "total_return",
        "annual_return",
        "sharpe",
        "max_drawdown",
        "num_days",
        "num_trades",
        "win_rate",
    ):
        assert key in stats

    assert stats["num_days"] == len(df)
    assert not np.isnan(stats["sharpe"])


def test_backtester_all_zero_signal_does_not_crash():
    df = _make_df([0] * 120)
    result = run_backtest(df, "signal", BacktestConfig())
    stats = result.stats

    assert stats["num_trades"] == 0
    assert stats["win_rate"] == 0.0
    assert not np.isnan(stats["total_return"])


def test_backtester_empty_signal_column_does_not_crash():
    df = _make_df([], n=0)
    df["signal"] = pd.Series(dtype=int)
    result = run_backtest(df, "signal", BacktestConfig())

    assert result.stats["num_days"] == 0
    assert result.stats["num_trades"] == 0
