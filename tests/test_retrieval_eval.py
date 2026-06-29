"""检索评测单元测试。"""

from __future__ import annotations

from pathlib import Path

from quant_agent.eval.retrieval_eval import recall_at_k, run_retrieval_eval
from quant_agent.evidence.models import EvidenceChunk

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_recall_at_k_keyword_match():
    case = {"relevant_keywords": ["supply", "chain"]}
    chunks = [
        EvidenceChunk(doc_id="a", text="unrelated", symbol="FIXTURE", doc_type="10-K", source="seed"),
        EvidenceChunk(doc_id="b", text="supply chain risk", symbol="FIXTURE", doc_type="10-K", source="seed"),
    ]
    assert recall_at_k(chunks, case, k=2) == 1.0


def test_run_retrieval_eval_offline():
    report = run_retrieval_eval(PROJECT_ROOT / "evalsets" / "retrieval_v1.yaml", k=5)
    assert report["benchmark"]["passed"] is True
    assert len(report["ablation"]) >= 3
    primary = report["benchmark"]["actual"]
    assert primary[f"recall@5"] >= 0.5
