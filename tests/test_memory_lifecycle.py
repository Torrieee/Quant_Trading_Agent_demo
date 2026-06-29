"""Memory 生命周期单元测试。"""

from __future__ import annotations

from quant_agent.evidence.memory import build_episodic_chunk
from quant_agent.evidence.memory_lifecycle import (
    consolidate_episodic_to_semantic,
    decide_memory_write,
    detect_conflicts,
    MemoryRecord,
)
from quant_agent.evidence.models import EvidenceChunk


def test_decide_memory_write_skips_duplicate():
    chunk = build_episodic_chunk(
        "FIXTURE",
        case_id="seed",
        task="t",
        decision={"signal_type": "hold", "confidence": 65},
        risk_verdict="pass",
        risk_reason=None,
        report="# R",
        final_state={"recommended_strategy": "mean_reversion"},
    )
    dec = decide_memory_write(
        "FIXTURE",
        case_id="run2",
        decision={"signal_type": "hold", "confidence": 70},
        risk_verdict="pass",
        report="# R2",
        final_state={"recommended_strategy": "mean_reversion"},
        recent_episodic=[chunk],
    )
    assert dec.should_write is False


def test_detect_conflicts_marks_contradicted():
    old = MemoryRecord(
        memory_id="m1",
        doc_id="d1",
        memory_type="episodic",
        content="x",
        source_run_id="s1",
        signal_type="buy",
        strategy="momentum",
        confidence=70,
        salience=0.8,
        created_at="2026-01-01",
        validation_status="verified",
    )
    new = MemoryRecord(
        memory_id="m2",
        doc_id="d2",
        memory_type="episodic",
        content="y",
        source_run_id="s2",
        signal_type="sell",
        strategy="mean_reversion",
        confidence=65,
        salience=0.8,
        created_at="2026-01-02",
    )
    meta = [{"memory_id": "m1", "memory_type": "episodic", "signal_type": "buy", "validation_status": "verified"}]
    updated = detect_conflicts("FIXTURE", new_record=new, existing_meta=meta)
    assert updated[0]["validation_status"] == "contradicted"
    assert new.validation_status == "unverified"


def test_consolidate_episodic_to_semantic():
    chunks = [
        EvidenceChunk(
            doc_id="e1",
            text=(
                "Episodic analysis memory for FIXTURE.\n"
                "Decision: hold (confidence 60%)\n"
                "Recommended strategy: mean_reversion\n"
                "Risk flags from evidence: supply_chain\n"
            ),
            symbol="FIXTURE",
            doc_type="episodic_memory",
            source="episodic_memory",
            title="e1",
            published_at="2026-01-01",
        ),
        EvidenceChunk(
            doc_id="e2",
            text=(
                "Episodic analysis memory for FIXTURE.\n"
                "Decision: hold (confidence 62%)\n"
                "Recommended strategy: mean_reversion\n"
                "Risk flags from evidence: none\n"
            ),
            symbol="FIXTURE",
            doc_type="episodic_memory",
            source="episodic_memory",
            title="e2",
            published_at="2026-01-02",
        ),
    ]
    facts = consolidate_episodic_to_semantic("FIXTURE", chunks)
    assert any("consolidation" in str(f.get("category", "")) for f in facts)
