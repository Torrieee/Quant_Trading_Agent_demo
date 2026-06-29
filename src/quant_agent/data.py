from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf
from loguru import logger

from .config import DataConfig

try:
    from .data_providers.openbb_client import (
        fetch_historical_ohlcv as openbb_fetch_ohlcv,
    )
    from .data_providers.openbb_client import fetch_stock_info as openbb_fetch_info

    _OPENBB_AVAILABLE = True
except ImportError:
    _OPENBB_AVAILABLE = False


def _cache_path(cfg: DataConfig) -> Path:
    cache_dir = Path(cfg.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{cfg.symbol}_{cfg.start}_{cfg.end or 'latest'}_{cfg.interval}.csv"
    return cache_dir / filename


def download_ohlcv(cfg: DataConfig, use_cache: bool = True) -> pd.DataFrame:
    """
    下载或读取缓存的 OHLCV 数据，返回按日期升序的 DataFrame。
    优先 OpenBB（可配置 FMP 等 provider），失败时回退 yfinance。
    """
    cache_file = _cache_path(cfg)

    if use_cache and cache_file.exists():
        logger.info(f"Loading cached data from {cache_file}")
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        df.index.name = "Date"
        return df

    data: Optional[pd.DataFrame] = None
    last_error: Exception | None = None

    if _OPENBB_AVAILABLE and cfg.interval in ("1d", "1day", "d"):
        try:
            data = openbb_fetch_ohlcv(
                cfg.symbol,
                start=cfg.start,
                end=cfg.end,
            )
        except Exception as exc:
            last_error = exc
            logger.warning(f"OpenBB 拉取失败，尝试 yfinance: {exc}")

    if data is None or data.empty:
        logger.info(
            f"yfinance 拉取: symbol={cfg.symbol}, start={cfg.start}, end={cfg.end}, "
            f"interval={cfg.interval}"
        )
        max_retries = 3
        for attempt in range(max_retries):
            try:
                data = yf.download(
                    cfg.symbol,
                    start=cfg.start,
                    end=cfg.end,
                    interval=cfg.interval,
                    auto_adjust=False,
                    progress=False,
                )
                if data is not None and not data.empty:
                    break
            except Exception as exc:
                last_error = exc
                logger.warning(f"yfinance 第 {attempt + 1} 次失败: {exc}")
                if attempt == max_retries - 1:
                    raise ValueError(
                        f"无法获取 {cfg.symbol} 行情。"
                        f"建议设置 FMP_API_KEY 使用 OpenBB（见 data_providers/openbb_client.py）。"
                        f" 最后错误: {exc}"
                    ) from exc

        if data is None or data.empty:
            msg = f"No data downloaded for symbol={cfg.symbol}"
            if last_error:
                msg += f" ({last_error})"
            raise ValueError(msg)

        if isinstance(data.columns, pd.MultiIndex):
            expected_cols = ["Adj Close", "Close", "High", "Low", "Open", "Volume"]
            if len(data.columns) == len(expected_cols):
                data.columns = expected_cols
            else:
                data.columns = data.columns.droplevel(0)
                if len(data.columns) == len(expected_cols):
                    data.columns = expected_cols

        required_cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
        available_cols = [col for col in required_cols if col in data.columns]
        if len(available_cols) != len(required_cols):
            missing = set(required_cols) - set(available_cols)
            raise ValueError(
                f"Missing required columns: {missing}. Available columns: {list(data.columns)}"
            )
        data = data[required_cols]

    if data.index.name is None or data.index.name != "Date":
        data.index.name = "Date"

    data = data.sort_index()
    data.to_csv(cache_file)
    logger.info(f"Saved data to cache: {cache_file}")
    return data


def get_stock_info(symbol: str) -> dict:
    """
    获取标的基本面信息（估值、股息等），供基本面智能体使用。
    优先 OpenBB profile，失败时回退 yfinance。
    """
    if _OPENBB_AVAILABLE:
        try:
            return openbb_fetch_info(symbol)
        except Exception as exc:
            logger.warning(f"OpenBB 基本面获取失败，回退 yfinance: {exc}")

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
    except Exception as exc:
        logger.warning(f"获取 {symbol} 基本面信息失败: {exc}")
        info = {}

    return {
        "symbol": symbol,
        "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
        "pb_ratio": info.get("priceToBook"),
        "dividend_yield": info.get("dividendYield") or 0.0,
        "market_cap": info.get("marketCap"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "previous_close": info.get("previousClose"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
    }


__all__ = ["download_ohlcv", "get_stock_info"]
