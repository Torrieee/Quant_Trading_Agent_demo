"""证据文档 ingest：基本面摘要、内置种子、可选 SEC。"""

from __future__ import annotations

import os
import re
from typing import Any

from loguru import logger

from .models import EvidenceChunk

# 内置种子文档（测试 FIXTURE 与常见美股 Demo，无需本地 MD 文件）
_SEED_LIBRARY: list[dict[str, Any]] = [
    {
        "symbol": "FIXTURE",
        "doc_type": "10-K",
        "section": "Item 1A Risk Factors",
        "title": "FIXTURE Corp Annual Risk Summary",
        "text": (
            "FIXTURE Corp faces supply chain concentration risk in Asia manufacturing. "
            "Any disruption could materially affect quarterly results. "
            "The company maintains diversified vendors but single-source components remain."
        ),
        "source": "seed",
        "source_url": "https://example.com/fixture/10k-risk",
    },
    {
        "symbol": "AAPL",
        "doc_type": "10-K",
        "section": "Item 1A Risk Factors",
        "title": "Apple Inc. Risk Factors Excerpt",
        "text": (
            "Apple depends on single-source and limited-source suppliers. "
            "Global supply chain disruptions may materially adversely affect operations. "
            "Competition and regulatory scrutiny remain significant risks."
        ),
        "source": "seed",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=AAPL",
    },
    {
        "symbol": "AAPL",
        "doc_type": "8-K",
        "section": "Item 2.02",
        "title": "Apple Quarterly Results",
        "text": (
            "Apple announced quarterly revenue growth in services segment. "
            "Management cited strong installed base and recurring revenue."
        ),
        "source": "seed",
        "source_url": "https://www.sec.gov/",
    },
]


def _chunk_id(symbol: str, doc_type: str, idx: int) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "_", symbol).strip("_")
    return f"{safe}_{doc_type}_{idx}"


def stock_info_to_chunks(symbol: str, stock_info: dict[str, Any]) -> list[EvidenceChunk]:
    """将 OpenBB/yfinance 基本面字段转为可检索文本。"""
    if not stock_info:
        return []
    lines = [
        f"Symbol: {symbol}",
        f"Sector: {stock_info.get('sector', 'N/A')}",
        f"Industry: {stock_info.get('industry', 'N/A')}",
        f"PE Ratio: {stock_info.get('pe_ratio', 'N/A')}",
        f"PB Ratio: {stock_info.get('pb_ratio', 'N/A')}",
        f"Dividend Yield: {stock_info.get('dividend_yield', 'N/A')}",
        f"Market Cap: {stock_info.get('market_cap', 'N/A')}",
        f"Current Price: {stock_info.get('current_price', 'N/A')}",
    ]
    text = "Company profile snapshot.\n" + "\n".join(lines)
    return [
        EvidenceChunk(
            doc_id=_chunk_id(symbol, "profile", 0),
            text=text,
            symbol=symbol.upper(),
            doc_type="profile",
            source="market_data",
            title=f"{symbol} Profile Snapshot",
        )
    ]


def seed_documents_for_symbol(symbol: str) -> list[EvidenceChunk]:
    """返回匹配 symbol 的内置种子文档。"""
    sym = symbol.upper()
    chunks: list[EvidenceChunk] = []
    idx = 0
    for item in _SEED_LIBRARY:
        if item["symbol"].upper() != sym:
            continue
        chunks.append(
            EvidenceChunk(
                doc_id=_chunk_id(sym, str(item["doc_type"]), idx),
                text=str(item["text"]),
                symbol=sym,
                doc_type=str(item["doc_type"]),
                source=str(item["source"]),
                title=str(item.get("title", "")),
                source_url=item.get("source_url"),
                section=item.get("section"),
            )
        )
        idx += 1
    return chunks


def analysis_report_to_chunk(symbol: str, report: str, *, analyzed_at: str) -> EvidenceChunk:
    """将一次 Engine 分析报告写入证据库（闭环）。"""
    preview = report[:2000] if len(report) > 2000 else report
    return EvidenceChunk(
        doc_id=f"{symbol.upper()}_internal_{analyzed_at.replace(':', '').replace(' ', '_')}",
        text=f"Prior analysis ({analyzed_at}):\n{preview}",
        symbol=symbol.upper(),
        doc_type="internal_analysis",
        source="engine_feedback",
        title=f"{symbol} Analysis Report",
        published_at=analyzed_at,
    )


def fetch_sec_chunks(symbol: str) -> list[EvidenceChunk]:
    """
    从 SEC EDGAR 拉取最近 filing 摘要（需网络）。
    默认启用；设置 EVIDENCE_FETCH_SEC=0 关闭。
    """
    from .config import is_sec_fetch_enabled

    if not is_sec_fetch_enabled():
        return []
    try:
        from .plugins.sec_edgar import fetch_sec_filing_excerpts

        return fetch_sec_filing_excerpts(symbol)
    except Exception as exc:
        logger.warning(f"SEC ingest 跳过 ({symbol}): {exc}")
        return []


def build_symbol_chunks(
    symbol: str,
    *,
    stock_info: dict[str, Any] | None = None,
    extra_chunks: list[EvidenceChunk] | None = None,
) -> list[EvidenceChunk]:
    """合并 profile、种子、SEC（可选）与额外片段。"""
    sym = symbol.upper()
    out: list[EvidenceChunk] = []
    out.extend(stock_info_to_chunks(sym, stock_info or {}))
    out.extend(seed_documents_for_symbol(sym))
    out.extend(fetch_sec_chunks(sym))
    try:
        from .plugins.news_feed import fetch_news_chunks

        out.extend(fetch_news_chunks(sym))
    except Exception as exc:
        logger.warning(f"新闻 ingest 跳过 ({sym}): {exc}")
    try:
        from .semantic_memory import facts_to_chunks, load_semantic_facts

        out.extend(facts_to_chunks(sym, load_semantic_facts(sym)))
    except Exception as exc:
        logger.warning(f"semantic memory 加载跳过 ({sym}): {exc}")
    if extra_chunks:
        out.extend(extra_chunks)
    # 去重 doc_id
    seen: set[str] = set()
    unique: list[EvidenceChunk] = []
    for c in out:
        if c.doc_id in seen:
            continue
        seen.add(c.doc_id)
        unique.append(c)
    return unique
