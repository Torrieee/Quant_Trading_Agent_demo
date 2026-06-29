"""OpenBB 数据接入：优先 FMP / Tiingo，避免 yfinance 限流。"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

import pandas as pd
from loguru import logger

# OpenBB 默认 provider 优先级：fmp → intrinio → tiingo → yfinance
# 配置 FMP_API_KEY 后通常可绕过 Yahoo 限流（免费档见 https://financialmodelingprep.com）


def _get_obb():
    try:
        from openbb import obb
    except ImportError as exc:
        raise ImportError(
            "未安装 OpenBB。请执行: pip install openbb"
        ) from exc
    return obb


def _apply_credentials_from_env() -> None:
    """从环境变量写入 OpenBB credentials。"""
    obb = _get_obb()
    mapping = {
        "fmp_api_key": ("FMP_API_KEY", "OPENBB_FMP_API_KEY"),
        "tiingo_token": ("TIINGO_TOKEN", "OPENBB_TIINGO_TOKEN"),
        "intrinio_api_key": ("INTRINIO_API_KEY", "OPENBB_INTRINIO_API_KEY"),
        "fred_api_key": ("FRED_API_KEY", "OPENBB_FRED_API_KEY"),
    }
    for field, env_names in mapping.items():
        value = next((os.environ.get(name) for name in env_names if os.environ.get(name)), None)
        if value:
            setattr(obb.user.credentials, field, value)


def get_active_provider() -> str | None:
    """
    返回当前将使用的 equity provider 名称；无可用密钥时可能为 yfinance。
    可通过环境变量 OPENBB_EQUITY_PROVIDER 强制指定（fmp / tiingo / yfinance 等）。
    """
    forced = os.environ.get("OPENBB_EQUITY_PROVIDER")
    if forced:
        return forced
    if os.environ.get("FMP_API_KEY") or os.environ.get("OPENBB_FMP_API_KEY"):
        return "fmp"
    if os.environ.get("TIINGO_TOKEN") or os.environ.get("OPENBB_TIINGO_TOKEN"):
        return "tiingo"
    if os.environ.get("INTRINIO_API_KEY") or os.environ.get("OPENBB_INTRINIO_API_KEY"):
        return "intrinio"
    return "yfinance"


def fetch_historical_ohlcv(
    symbol: str,
    *,
    start: dt.date,
    end: dt.date | None = None,
    provider: str | None = None,
) -> pd.DataFrame:
    """通过 OpenBB 拉取 OHLCV，返回标准列名的 DataFrame。"""
    obb = _get_obb()
    _apply_credentials_from_env()
    provider = provider or get_active_provider()
    end = end or dt.date.today()

    logger.info(
        f"OpenBB 拉取行情: symbol={symbol}, start={start}, end={end}, provider={provider}"
    )

    kwargs: dict[str, Any] = {
        "symbol": symbol,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }
    if provider:
        kwargs["provider"] = provider

    try:
        result = obb.equity.price.historical(**kwargs)
        df = result.to_dataframe()
    except Exception as exc:
        raise ValueError(
            f"OpenBB 获取 {symbol} 行情失败（provider={provider}）: {exc}"
        ) from exc

    if df is None or df.empty:
        hint = ""
        if provider == "yfinance":
            hint = (
                " Yahoo 数据源可能被限流。请设置免费 FMP_API_KEY 后重试，"
                "参见 https://financialmodelingprep.com"
            )
        raise ValueError(f"OpenBB 未返回 {symbol} 的行情数据。{hint}")

    return _normalize_ohlcv(df)


def fetch_stock_info(symbol: str, *, provider: str | None = None) -> dict[str, Any]:
    """通过 OpenBB profile 获取基本面摘要。"""
    obb = _get_obb()
    _apply_credentials_from_env()
    provider = provider or get_active_provider()

    info: dict[str, Any] = {"symbol": symbol}
    try:
        kwargs: dict[str, Any] = {"symbol": symbol}
        if provider in ("fmp", "intrinio", "yfinance"):
            kwargs["provider"] = provider
        profile = obb.equity.profile(**kwargs)
        pdf = profile.to_dataframe()
        if pdf is not None and not pdf.empty:
            row = pdf.iloc[0]
            info.update(_profile_row_to_info(row, symbol))
            return info
    except Exception as exc:
        logger.warning(f"OpenBB profile 获取失败 ({symbol}, {provider}): {exc}")

    # profile 失败时，用最近收盘价补全
    try:
        hist = fetch_historical_ohlcv(
            symbol,
            start=dt.date.today() - dt.timedelta(days=30),
            provider=provider,
        )
        if not hist.empty:
            info.setdefault("current_price", float(hist["Close"].iloc[-1]))
    except Exception as exc:
        logger.warning(f"无法从行情补全 {symbol} 价格: {exc}")

    return info


def _profile_row_to_info(row: pd.Series, symbol: str) -> dict[str, Any]:
    """将 OpenBB profile 行映射为 get_stock_info 字段。"""
    def pick(*keys: str, default=None):
        for key in keys:
            if key in row.index and pd.notna(row[key]):
                return row[key]
        return default

    pe = pick("pe_ratio", "pe", "trailing_pe", "price_to_earnings")
    pb = pick("pb_ratio", "pb", "price_to_book")
    div = pick("dividend_yield", "last_div", "dividend_yield_pct")
    if div is not None:
        try:
            div = float(div)
            if div > 1:
                div = div / 100.0
        except (TypeError, ValueError):
            div = None

    return {
        "symbol": pick("symbol", default=symbol),
        "pe_ratio": _to_float(pe),
        "pb_ratio": _to_float(pb),
        "dividend_yield": div or 0.0,
        "market_cap": _to_float(pick("market_cap", "mktcap", "market_capitalization")),
        "current_price": _to_float(
            pick("price", "last_price", "close", "regular_market_price")
        ),
        "previous_close": _to_float(pick("previous_close", "prev_close")),
        "sector": pick("sector", "sector_name"),
        "industry": pick("industry", "industry_category"),
    }


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """统一为 Open / High / Low / Close / Adj Close / Volume 列。"""
    out = df.copy()

    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [
            str(level[0]).lower() if isinstance(level, tuple) else str(level).lower()
            for level in out.columns
        ]
    else:
        out.columns = [str(c).lower().replace(" ", "_") for c in out.columns]

    if "date" in out.columns and out.index.name != "date":
        out = out.set_index("date")

    rename_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "adj_close": "Adj Close",
        "adjusted_close": "Adj Close",
        "volume": "Volume",
    }
    out = out.rename(columns={k: v for k, v in rename_map.items() if k in out.columns})

    if "Adj Close" not in out.columns and "Close" in out.columns:
        out["Adj Close"] = out["Close"]

    required = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"OpenBB 返回数据缺少列: {missing}，实际列: {list(out.columns)}")

    out = out[required].sort_index()
    out.index = pd.to_datetime(out.index)
    out.index.name = "Date"
    return out


def _to_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
