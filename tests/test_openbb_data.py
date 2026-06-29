"""OpenBB 数据层单元测试。"""

from __future__ import annotations

import pandas as pd

from quant_agent.data_providers.openbb_client import _normalize_ohlcv, get_active_provider


def test_normalize_ohlcv_lowercase_columns():
    df = pd.DataFrame(
        {
            "open": [1.0, 2.0],
            "high": [1.1, 2.1],
            "low": [0.9, 1.9],
            "close": [1.05, 2.05],
            "volume": [100, 200],
        },
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )
    out = _normalize_ohlcv(df)
    assert list(out.columns) == ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    assert len(out) == 2


def test_get_active_provider_prefers_fmp(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    assert get_active_provider() == "fmp"
