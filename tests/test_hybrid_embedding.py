"""Hybrid Embedding 检索测试。"""

from __future__ import annotations

from quant_agent.evidence import EvidenceRetriever
from quant_agent.evidence.models import EvidenceChunk
from quant_agent.evidence.store import HybridEvidenceIndex


def test_hybrid_search_ranks_supply_chain(monkeypatch):
    monkeypatch.setenv("EVIDENCE_SEARCH_MODE", "hybrid")
    monkeypatch.setenv("EVIDENCE_FETCH_SEC", "0")

    index = HybridEvidenceIndex()
    chunks = [
        EvidenceChunk(
            doc_id="a",
            text="Apple services revenue grew strongly in the latest quarter.",
            symbol="FIXTURE",
            doc_type="8-K",
            source="seed",
            title="Results",
        ),
        EvidenceChunk(
            doc_id="b",
            text="FIXTURE Corp faces supply chain concentration risk in Asia manufacturing.",
            symbol="FIXTURE",
            doc_type="10-K",
            source="seed",
            title="Risk",
        ),
    ]
    index.upsert("FIXTURE", chunks)
    hits = index.search("FIXTURE", "supply chain disruption risk", top_k=2)
    assert hits
    assert hits[0].doc_id == "b"


def test_tfidf_mode_still_works(monkeypatch):
    monkeypatch.setenv("EVIDENCE_SEARCH_MODE", "tfidf")
    monkeypatch.setenv("EVIDENCE_FETCH_SEC", "0")

    retriever = EvidenceRetriever()
    retriever.ensure_index("FIXTURE", stock_info={"symbol": "FIXTURE", "sector": "Tech"})
    out = retriever.search("FIXTURE", "supply chain", top_k=3)
    assert out
    assert any("supply chain" in c.text.lower() for c in out)


def test_embedding_mode_uses_dense_vectors(monkeypatch):
    monkeypatch.setenv("EVIDENCE_SEARCH_MODE", "embedding")
    monkeypatch.setenv("EVIDENCE_FETCH_SEC", "0")

    index = HybridEvidenceIndex()
    index.upsert(
        "X",
        [
            EvidenceChunk(
                doc_id="1",
                text="regulatory investigation subpoena risk",
                symbol="X",
                doc_type="10-K",
                source="seed",
                title="Reg",
            ),
            EvidenceChunk(
                doc_id="2",
                text="strong dividend growth and buybacks",
                symbol="X",
                doc_type="profile",
                source="seed",
                title="Div",
            ),
        ],
    )
    hits = index.search("X", "regulatory scrutiny", top_k=1)
    assert hits[0].doc_id == "1"
