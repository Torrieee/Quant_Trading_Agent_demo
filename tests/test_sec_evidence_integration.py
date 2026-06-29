"""SEC EDGAR 证据 ingest 集成测试（需网络，默认跳过）。"""

from __future__ import annotations

import os

import pytest

from quant_agent.evidence import EvidenceRetriever
from quant_agent.evidence.plugins.sec_edgar import fetch_sec_filing_excerpts


@pytest.mark.integration
def test_sec_edgar_fetch_aapl(monkeypatch):
    """直连 SEC 拉取 AAPL 最近 10-K/10-Q 摘要。"""
    monkeypatch.setenv("EVIDENCE_FETCH_SEC", "1")
    chunks = fetch_sec_filing_excerpts("AAPL", max_chars=3000)
    assert chunks, "SEC 未返回片段（检查网络、User-Agent 或 sec.gov 可达性）"
    c = chunks[0]
    assert c.source == "sec_edgar"
    assert c.doc_type in ("10-K", "10-Q")
    assert c.source_url and "sec.gov" in c.source_url
    assert len(c.text) >= 200


@pytest.mark.integration
def test_evidence_retriever_includes_sec_for_aapl(monkeypatch):
    """EvidenceRetriever 索引应含 SEC 来源 chunk。"""
    monkeypatch.setenv("EVIDENCE_FETCH_SEC", "1")
    retriever = EvidenceRetriever()
    count = retriever.ensure_index("AAPL", stock_info={"symbol": "AAPL", "sector": "Technology"})
    assert count >= 1
    snapshot = retriever.get_snapshot("AAPL", "risk factors revenue outlook")
    sources = {c.source for c in snapshot}
    assert "sec_edgar" in sources or any(c.doc_type in ("10-K", "10-Q") for c in snapshot)


def _integration_enabled() -> bool:
    return os.environ.get("RUN_SEC_INTEGRATION", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


pytestmark = pytest.mark.skipif(
    not _integration_enabled(),
    reason="设置 RUN_SEC_INTEGRATION=1 以运行 SEC 网络集成测试",
)
