"""Episodic Memory 持久化与跨次 analyze 测试。"""

from __future__ import annotations

from quant_agent.evidence import EvidenceRetriever
from quant_agent.evidence.memory import build_episodic_chunk, is_episodic_chunk


def _ingest_sample(retriever: EvidenceRetriever, symbol: str, signal: str, case: str) -> None:
    retriever.ingest_episodic_session(
        symbol,
        case_id=case,
        task=f"Analyze {symbol} for {signal}",
        decision={"signal_type": signal, "confidence": 70, "reasoning": f"vote {signal}"},
        risk_verdict="pass",
        risk_reason=None,
        report=f"# Report\n\nDecision was {signal} for {symbol}.",
        final_state={"recommended_strategy": "momentum", "risk_flags": []},
    )


def test_episodic_survives_ensure_index(monkeypatch):
    monkeypatch.setenv("EVIDENCE_FETCH_SEC", "0")

    r1 = EvidenceRetriever()
    _ingest_sample(r1, "FIXTURE", "hold", "case_a")
    assert len(r1.list_episodic("FIXTURE")) >= 1

    r1.ensure_index("FIXTURE", stock_info={"symbol": "FIXTURE", "sector": "Tech"})
    assert len(r1.list_episodic("FIXTURE")) >= 1


def test_episodic_persists_across_new_retriever_instance(monkeypatch):
    monkeypatch.setenv("EVIDENCE_FETCH_SEC", "0")

    r1 = EvidenceRetriever()
    _ingest_sample(r1, "FIXTURE", "buy", "persist_case")

    r2 = EvidenceRetriever()
    episodic = r2.list_episodic("FIXTURE")
    assert episodic
    assert any("buy" in c.text.lower() for c in episodic)


def test_snapshot_includes_episodic_memory(monkeypatch):
    monkeypatch.setenv("EVIDENCE_FETCH_SEC", "0")

    retriever = EvidenceRetriever()
    _ingest_sample(retriever, "FIXTURE", "sell", "snap_case")
    retriever.ensure_index("FIXTURE")

    snapshot = retriever.get_snapshot("FIXTURE", "prior analysis decision")
    state = retriever.snapshot_to_state(snapshot, symbol="FIXTURE")

    assert state.get("episodic_memory")
    assert any(is_episodic_chunk(c) for c in snapshot)


def test_build_episodic_chunk_fields():
    chunk = build_episodic_chunk(
        "AAPL",
        case_id="t1",
        task="test task",
        decision={"signal_type": "hold", "confidence": 55},
        risk_verdict="pass",
        risk_reason=None,
        report="hello",
        final_state={"recommended_strategy": "mean_reversion"},
        analyzed_at="2026-06-28 12:00 UTC",
    )
    assert chunk.doc_type == "episodic_memory"
    assert "hold" in chunk.text
    assert "mean_reversion" in chunk.text
