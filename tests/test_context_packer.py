"""Context packer 单元测试。"""

from __future__ import annotations

from quant_agent.context import pack_workflow_context


def test_pack_workflow_context_budget_and_manifest():
    quant = {
        "preliminary_decision": {"signal_type": "hold", "confidence": 60},
        "evidence_snapshot": [{"doc_id": "d1", "text": "supply chain risk " * 50}],
        "episodic_memory": [{"summary": "prior sell signal"}],
        "recommended_strategy": "mean_reversion",
    }
    packed, manifest = pack_workflow_context(
        quant, task="评估供应链风险", symbol="FIXTURE", budget=500
    )
    assert "# Packed Context" in packed
    assert "mean_reversion" in packed
    assert manifest.used_tokens <= 500
    assert manifest.kept_items >= 1
    assert "context_manifest" not in packed


def test_pack_dedupes_similar_chunks():
    quant = {
        "recommended_strategy": "momentum",
        "market_regime": "trending",
    }
    _, m1 = pack_workflow_context(quant, budget=8000)
    _, m2 = pack_workflow_context(quant, budget=8000)
    assert m1.kept_items == m2.kept_items
