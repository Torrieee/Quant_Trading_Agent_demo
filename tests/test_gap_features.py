"""除 Eval 外前沿 gap 补齐项单元测试。"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from quant_agent.compliance.audit_log import append_audit_record
from quant_agent.compliance.guardrails import sanitize_report_text, validate_decision
from quant_agent.evidence.document_signal import revise_decision_from_evidence
from quant_agent.evidence.models import EvidenceChunk
from quant_agent.evidence.query_expand import expand_query
from quant_agent.evidence.rerank import rerank_chunks
from quant_agent.evidence.semantic_memory import extract_facts_from_text
from quant_agent.execution.paper_trading import load_portfolio, submit_paper_order

TESTS_DIR = Path(__file__).parent


def test_document_signal_downgrades_buy_on_going_concern():
    prelim = {
        "signal_type": "buy",
        "confidence": 80,
        "reasoning": "x",
        "scores": {"buy": 80, "sell": 10, "hold": 10},
    }
    out = revise_decision_from_evidence(prelim, risk_flags=["going_concern"], event_severity="high")
    assert out["document_signal"]["applied"]
    assert out["confidence"] <= 35 or out["signal_type"] != "buy"


def test_query_expand_produces_variants():
    variants = expand_query("vendor concentration risk")
    assert len(variants) >= 1
    assert variants[0] == "vendor concentration risk"


def test_rerank_prefers_overlap():
    chunks = [
        EvidenceChunk(
            doc_id="a",
            text="unrelated revenue growth",
            symbol="X",
            doc_type="10-K",
            source="seed",
            title="a",
            score=0.9,
        ),
        EvidenceChunk(
            doc_id="b",
            text="supply chain disruption Asia vendors",
            symbol="X",
            doc_type="10-K",
            source="seed",
            title="b",
            score=0.3,
        ),
    ]
    ranked = rerank_chunks("supply chain risk", chunks, top_k=1)
    assert ranked[0].doc_id == "b"


def test_semantic_fact_extract():
    facts = extract_facts_from_text("FIXTURE", "We face supply chain concentration risk.", source="test")
    assert facts
    assert facts[0]["category"] == "supply_chain"


def test_paper_trading_roundtrip(monkeypatch):
    path = TESTS_DIR / "_paper_tmp" / f"{uuid.uuid4().hex}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PAPER_PORTFOLIO_PATH", str(path))
    try:
        r1 = submit_paper_order("AAPL", "buy", 10, 100.0, case_id="t1")
        assert r1.get("status") == "filled"
        pf = load_portfolio()
        assert pf["positions"]["AAPL"]["qty"] == 10
    finally:
        path.unlink(missing_ok=True)


def test_audit_log_append(monkeypatch):
    path = TESTS_DIR / "_audit_tmp" / f"{uuid.uuid4().hex}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AUDIT_LOG_PATH", str(path))
    append_audit_record({"case_id": "c1", "symbol": "AAPL"})
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["symbol"] == "AAPL"
    path.unlink(missing_ok=True)


def test_guardrails_add_disclaimer():
    out = sanitize_report_text("# Report\n\nBuy now guaranteed profit.")
    assert out
    assert "免责声明" in out
    assert "guaranteed" not in out.lower() or "过滤" in out


def test_validate_decision_warns_high_confidence():
    w = validate_decision({"signal_type": "buy", "confidence": 99})
    assert w
