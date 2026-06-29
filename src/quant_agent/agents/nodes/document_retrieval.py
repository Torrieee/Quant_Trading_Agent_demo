"""Document retrieval：ingest + 预检索 + document_signal 修正决策。"""

from __future__ import annotations

from typing import Any

from ..serialization import resolve_analysis_data
from ...evidence import EvidenceRetriever
from ...evidence.document_signal import revise_decision_from_evidence
from ..state import WorkflowState

_retriever: EvidenceRetriever | None = None


def _get_retriever() -> EvidenceRetriever:
    global _retriever
    if _retriever is None:
        _retriever = EvidenceRetriever.get_default()
    return _retriever


def document_retrieval_node(state: WorkflowState) -> WorkflowState:
    """构建证据索引、预检索，并基于披露修正 preliminary_decision。"""
    visited = list(state.get("agents_visited") or [])
    if "document_retrieval" not in visited:
        visited.append("document_retrieval")

    symbol = state.get("symbol") or "UNKNOWN"
    task = state.get("task") or ""
    analysis_data = resolve_analysis_data(state)
    stock_info = analysis_data.get("stock_info") or {}
    quant_state = dict(state.get("quant_state") or {})
    trace_steps = list(state.get("trace_steps") or [])
    preliminary = dict(
        state.get("preliminary_decision") or quant_state.get("preliminary_decision") or {}
    )

    retriever = _get_retriever()
    chunk_count = retriever.ensure_index(symbol, stock_info=stock_info)
    snapshot = retriever.get_snapshot(symbol, task, top_k=8)
    evidence_fields = retriever.snapshot_to_state(snapshot, symbol=symbol)

    quant_state["symbol"] = symbol
    quant_state.update(evidence_fields)

    doc_flags = evidence_fields.get("document_flags") or {}
    revised = revise_decision_from_evidence(
        preliminary,
        risk_flags=list(evidence_fields.get("risk_flags") or []),
        event_severity=str(doc_flags.get("event_severity", "low")),
    )
    quant_state["preliminary_decision"] = revised
    quant_state["document_signal"] = revised.get("document_signal")

    existing_docs: list[dict] = list(quant_state.get("retrieved_documents") or [])
    seen_ids = {d.get("doc_id") for d in existing_docs if isinstance(d, dict)}
    for doc in evidence_fields.get("evidence_snapshot") or []:
        if isinstance(doc, dict) and doc.get("doc_id") not in seen_ids:
            existing_docs.append(doc)
            seen_ids.add(doc.get("doc_id"))
    quant_state["retrieved_documents"] = existing_docs

    trace_steps.append(
        {
            "agent": "document_retrieval",
            "tool_name": "evidence_index",
            "arguments": {"symbol": symbol, "task": task[:120]},
            "observation": {
                "chunk_count": chunk_count,
                "snapshot_count": len(snapshot),
                "episodic_count": len(evidence_fields.get("episodic_memory") or []),
                "semantic_count": len(evidence_fields.get("semantic_memory") or []),
                "document_flags": evidence_fields.get("document_flags"),
                "document_signal": revised.get("document_signal"),
            },
            "latency_ms": 0.0,
            "status": "ok",
            "rationale": "Evidence 索引、预检索与 document_signal 决策修正",
        }
    )

    return WorkflowState(
        quant_state=quant_state,
        preliminary_decision=revised,
        trace_steps=trace_steps,
        agents_visited=visited,
        retrieval_complete=True,
        step_count=state.get("step_count", 0) + 1,
    )


def set_evidence_retriever(retriever: EvidenceRetriever | None) -> None:
    global _retriever
    _retriever = retriever
