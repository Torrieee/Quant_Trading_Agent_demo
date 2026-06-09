"""Shared pytest fixtures."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quant_agent.config import AgentConfig, BacktestConfig, DataConfig, StrategyConfig
from quant_agent.features import add_daily_returns

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURE_CSV = FIXTURES_DIR / "sample_ohlcv.csv"


def _build_sample_ohlcv(n: int = 150, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n)
    returns = rng.normal(0.0005, 0.015, size=n)
    close = 100 * np.cumprod(1 + returns)
    high = close * (1 + rng.uniform(0, 0.01, n))
    low = close * (1 - rng.uniform(0, 0.01, n))
    open_ = close * (1 + rng.normal(0, 0.002, n))
    volume = rng.integers(1_000_000, 5_000_000, size=n)
    df = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates,
    )
    return add_daily_returns(df)


@pytest.fixture(scope="session", autouse=True)
def ensure_fixture_csv() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    if not FIXTURE_CSV.exists():
        _build_sample_ohlcv().to_csv(FIXTURE_CSV)


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    if FIXTURE_CSV.exists():
        df = pd.read_csv(FIXTURE_CSV, index_col=0, parse_dates=True)
    else:
        df = _build_sample_ohlcv()
    if "ret" not in df.columns:
        df = add_daily_returns(df)
    return df


@pytest.fixture
def agent_config() -> AgentConfig:
    return AgentConfig(
        data=DataConfig(symbol="FIXTURE", start=date(2020, 1, 1)),
        strategy=StrategyConfig(name="mean_reversion"),
        backtest=BacktestConfig(initial_cash=100_000),
    )


@pytest.fixture
def mock_download_ohlcv(sample_ohlcv, monkeypatch):
    def _mock(_cfg: DataConfig) -> pd.DataFrame:
        return sample_ohlcv.copy()

    monkeypatch.setattr("quant_agent.agent.download_ohlcv", _mock)
    return _mock
