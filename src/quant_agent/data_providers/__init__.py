"""外部行情与基本面数据接入。"""

from .openbb_client import fetch_historical_ohlcv, fetch_stock_info, get_active_provider

__all__ = ["fetch_historical_ohlcv", "fetch_stock_info", "get_active_provider"]
