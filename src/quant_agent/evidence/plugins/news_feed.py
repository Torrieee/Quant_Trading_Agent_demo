"""新闻 / 另类数据插件（yfinance，无需额外 API）。"""

from __future__ import annotations

import os

from loguru import logger

from ..models import EvidenceChunk


def fetch_news_chunks(symbol: str, *, max_items: int = 5) -> list[EvidenceChunk]:
    """拉取 yfinance 新闻标题与摘要作为可检索 chunk。"""
    if os.environ.get("EVIDENCE_FETCH_NEWS", "1").strip().lower() in ("0", "false", "no", "off"):
        return []
    sym = symbol.upper()
    try:
        import yfinance as yf

        ticker = yf.Ticker(sym)
        news = getattr(ticker, "news", None) or []
    except Exception as exc:
        logger.warning(f"新闻 ingest 跳过 ({sym}): {exc}")
        return []

    chunks: list[EvidenceChunk] = []
    for i, item in enumerate(news[:max_items]):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        summary = str(item.get("summary") or item.get("link") or "")
        text = f"{title}. {summary}".strip()
        if len(text) < 20:
            continue
        pub = item.get("providerPublishTime")
        published = str(pub) if pub else None
        chunks.append(
            EvidenceChunk(
                doc_id=f"{sym}_NEWS_{i}",
                text=text,
                symbol=sym,
                doc_type="news",
                source="yfinance_news",
                title=title or f"{sym} news",
                published_at=published,
                source_url=item.get("link"),
                section="news",
            )
        )
    return chunks
