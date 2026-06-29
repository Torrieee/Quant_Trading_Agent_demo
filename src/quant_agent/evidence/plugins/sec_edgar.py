"""SEC EDGAR 插件（默认启用，需网络；EVIDENCE_FETCH_SEC=0 可关闭）。"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from http.client import IncompleteRead
from pathlib import Path

from loguru import logger

from ..config import sec_user_agent
from ..chunking import split_filing_text
from ..models import EvidenceChunk

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_CACHE_DIR = Path(os.environ.get("EVIDENCE_CACHE_DIR", "data_cache")) / "sec"
_TICKERS_CACHE = _CACHE_DIR / "company_tickers.json"

# 常见 ticker → CIK，网络不稳定时作 fallback
_KNOWN_CIK: dict[str, str] = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "GOOG": "0001652044",
    "AMZN": "0001018724",
    "META": "0001326801",
    "TSLA": "0001318605",
    "NVDA": "0001045810",
}


def _http_get(
    url: str,
    timeout: float = 45.0,
    *,
    max_bytes: int | None = None,
    retries: int = 3,
) -> bytes:
    """GET；max_bytes 为 None 时读全量；IncompleteRead 时重试。"""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": sec_user_agent()},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if max_bytes is None:
                    return resp.read()
                chunks: list[bytes] = []
                total = 0
                while total < max_bytes:
                    block = resp.read(min(65536, max_bytes - total))
                    if not block:
                        break
                    chunks.append(block)
                    total += len(block)
                return b"".join(chunks)
        except IncompleteRead as exc:
            last_err = exc
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_err = exc
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    if last_err:
        raise last_err
    return b""


def _http_get_json(url: str, timeout: float = 45.0) -> dict:
    return json.loads(_http_get(url, timeout=timeout, max_bytes=None).decode("utf-8"))


def _load_ticker_index() -> dict:
    """加载 ticker→CIK 索引（本地缓存优先）。"""
    if _TICKERS_CACHE.is_file():
        try:
            return json.loads(_TICKERS_CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("SEC ticker 缓存损坏，将重新下载")

    data = _http_get_json(_TICKERS_URL)
    _TICKERS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    _TICKERS_CACHE.write_text(json.dumps(data), encoding="utf-8")
    return data


def _resolve_cik(symbol: str) -> str | None:
    sym = symbol.upper()
    if sym in _KNOWN_CIK:
        return _KNOWN_CIK[sym]

    try:
        data = _load_ticker_index()
        for entry in data.values():
            if str(entry.get("ticker", "")).upper() == sym:
                return str(entry["cik_str"]).zfill(10)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, IncompleteRead) as exc:
        logger.warning(f"SEC ticker 解析失败: {exc}")
        if sym in _KNOWN_CIK:
            return _KNOWN_CIK[sym]
    return _KNOWN_CIK.get(sym)


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_sec_filing_excerpts(symbol: str, *, max_chars: int = 4000) -> list[EvidenceChunk]:
    """拉取最近一份 10-K 或 10-Q 的文本摘要片段。"""
    cik = _resolve_cik(symbol)
    if not cik:
        return []

    sub_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        sub = _http_get_json(sub_url)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, IncompleteRead) as exc:
        logger.warning(f"SEC submissions 失败: {exc}")
        return []

    recent = sub.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    filing_dates = recent.get("filingDate", [])

    target_idx = None
    for i, form in enumerate(forms):
        if form in ("10-K", "10-Q"):
            target_idx = i
            break
    if target_idx is None:
        return []

    accession_raw = str(accessions[target_idx])
    accession = accession_raw.replace("-", "")
    primary = str(primary_docs[target_idx])
    form = str(forms[target_idx])
    filed = str(filing_dates[target_idx]) if target_idx < len(filing_dates) else None
    cik_int = str(int(cik))

    candidates = [
        f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/{accession_raw}.txt",
        f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/{primary}",
    ]

    plain = ""
    doc_url = candidates[0]
    for url in candidates:
        try:
            raw = _http_get(url, max_bytes=512_000)
            text = raw.decode("utf-8", errors="ignore")
            if "<html" in text.lower()[:500]:
                plain = _strip_html(text)
            else:
                plain = re.sub(r"\s+", " ", text).strip()
            if len(plain) >= 200:
                doc_url = url
                break
        except (urllib.error.URLError, TimeoutError, OSError, IncompleteRead) as exc:
            logger.warning(f"SEC 文档下载失败 ({url}): {exc}")
            continue

    plain = plain[:max_chars * 2]
    if len(plain) < 200:
        return []

    sections = split_filing_text(
        symbol,
        plain,
        form=form,
        source_url=doc_url,
        published_at=filed,
    )
    if sections:
        return sections

    return [
        EvidenceChunk(
            doc_id=f"{symbol.upper()}_SEC_{form}_{filed or 'latest'}",
            text=plain[:max_chars],
            symbol=symbol.upper(),
            doc_type=form,
            source="sec_edgar",
            title=f"{symbol.upper()} {form} excerpt",
            published_at=filed,
            source_url=doc_url,
            section="filing_excerpt",
        )
    ]
