from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf
from loguru import logger

from .config import DataConfig


def _cache_path(cfg: DataConfig) -> Path:
    cache_dir = Path(cfg.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{cfg.symbol}_{cfg.start}_{cfg.end or 'latest'}_{cfg.interval}.csv"
    return cache_dir / filename


def download_ohlcv(cfg: DataConfig, use_cache: bool = True) -> pd.DataFrame:
    """
    下载或读取缓存的 OHLCV 数据，返回按日期升序的 DataFrame。
    """
    cache_file = _cache_path(cfg)

    if use_cache and cache_file.exists():
        logger.info(f"Loading cached data from {cache_file}")
        # 读取时，Date 应该是 index
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        df.index.name = "Date"
        return df

    logger.info(
        f"Downloading data: symbol={cfg.symbol}, start={cfg.start}, end={cfg.end}, "
        f"interval={cfg.interval}"
    )
    
    # 尝试下载，如果失败则重试
    max_retries = 3
    data: Optional[pd.DataFrame] = None
    
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
        except Exception as e:
            logger.warning(f"Download attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise ValueError(f"Failed to download data for symbol={cfg.symbol} after {max_retries} attempts: {e}")

    if data is None or data.empty:
        raise ValueError(f"No data downloaded for symbol={cfg.symbol}")

    # 处理 MultiIndex 列（yfinance 可能返回）
    if isinstance(data.columns, pd.MultiIndex):
        # yfinance 返回的列顺序固定为：Adj Close, Close, High, Low, Open, Volume
        # 直接根据列数和位置重命名，不依赖 MultiIndex 层级
        expected_cols = ["Adj Close", "Close", "High", "Low", "Open", "Volume"]
        if len(data.columns) == len(expected_cols):
            data.columns = expected_cols
        else:
            # 如果列数不匹配，尝试移除第一层后重命名
            data.columns = data.columns.droplevel(0)
            if len(data.columns) == len(expected_cols):
                data.columns = expected_cols
    
    # 选择需要的列
    required_cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    # 只选择存在的列
    available_cols = [col for col in required_cols if col in data.columns]
    if len(available_cols) != len(required_cols):
        missing = set(required_cols) - set(available_cols)
        raise ValueError(f"Missing required columns: {missing}. Available columns: {list(data.columns)}")
    data = data[required_cols]

    # 确保 Date 是 index
    if data.index.name is None or data.index.name != "Date":
        data.index.name = "Date"
    
    logger.debug(f"Final data shape: {data.shape}, columns: {list(data.columns)}")
    data = data.sort_index()

    # 保存时，Date 作为 index 保存（index=True 是默认值）
    data.to_csv(cache_file)
    logger.info(f"Saved data to cache: {cache_file}")
    return data


__all__ = ["download_ohlcv"]


