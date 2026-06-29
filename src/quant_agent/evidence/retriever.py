"""Evidence 检索入口：ingest + snapshot + episodic memory。"""

from __future__ import annotations

import datetime as dt
from typing import Any

from .document_rules import build_document_flags, extract_risk_flags
from .ingest import build_symbol_chunks
from .memory import build_episodic_chunk, is_episodic_chunk, merge_chunk_lists
from .models import EvidenceChunk
from .persistence import load_symbol_chunks, save_symbol_chunks
from .query_expand import expand_query
from .rerank import rerank_chunks
from .semantic_memory import ingest_semantic_from_session
from .store import HybridEvidenceIndex, TfidfEvidenceIndex

_default_retriever: EvidenceRetriever | None = None


class EvidenceRetriever:
    """证据层门面：外部披露 + 跨会话 Episodic Memory。"""

    def __init__(self) -> None:
        self._index = HybridEvidenceIndex()

    def _now_iso(self) -> str:
        return dt.datetime.now(dt.timezone.utc).isoformat()

    def _load_persisted(self, symbol: str) -> list[EvidenceChunk]:
        chunks, _ = load_symbol_chunks(symbol)
        if chunks:
            self._index.upsert(symbol, chunks, updated_at=self._now_iso())
        return chunks

    def _persist(self, symbol: str) -> None:
        chunks = self._index.get_chunks(symbol)
        save_symbol_chunks(symbol, chunks, updated_at=self._now_iso())

    def ensure_index(
        self,
        symbol: str,
        *,
        stock_info: dict[str, Any] | None = None,
        extra_chunks: list[EvidenceChunk] | None = None,
        force_refresh_external: bool = False,
    ) -> int:
        """
        构建或增量合并 symbol 索引。
        - 首次或 force：从磁盘加载 episodic
        - 外部证据（profile/SEC/seed）与已有 episodic merge，不覆盖记忆
        """
        sym = symbol.upper()
        if not self._index.has_symbol(sym):
            self._load_persisted(sym)

        existing = self._index.get_chunks(sym) if self._index.has_symbol(sym) else []
        if not existing and not force_refresh_external:
            existing, _ = load_symbol_chunks(sym)

        fresh = build_symbol_chunks(sym, stock_info=stock_info, extra_chunks=extra_chunks)
        merged = merge_chunk_lists(existing, fresh)
        self._index.upsert(sym, merged, updated_at=self._now_iso())
        self._persist(sym)
        return len(merged)

    def get_snapshot(
        self,
        symbol: str,
        task: str,
        *,
        top_k: int = 6,
    ) -> list[EvidenceChunk]:
        """按 task 与 symbol 预检索；优先包含 prior episodic memory。"""
        sym = symbol.upper()
        if not self._index.has_symbol(sym):
            self.ensure_index(sym)

        queries = [
            f"{sym} prior analysis decision rationale strategy",
            f"{sym} risk factors supply chain regulatory",
            f"{sym} business outlook revenue",
            task,
        ]
        seen: set[str] = set()
        out: list[EvidenceChunk] = []

        # 至少保留 1 条最新 episodic（若存在）
        episodic = [
            c
            for c in self._index.get_chunks(sym)
            if is_episodic_chunk(c)
        ]
        episodic.sort(key=lambda c: c.published_at or "", reverse=True)
        if episodic:
            out.append(episodic[0])
            seen.add(episodic[0].doc_id)

        for q in queries:
            for chunk in self.search_multi(sym, q, top_k=max(2, top_k // 2), prefer_episodic=("prior" in q or "analysis" in q)):
                if chunk.doc_id in seen:
                    continue
                seen.add(chunk.doc_id)
                out.append(chunk)
                if len(out) >= top_k:
                    return out
        return out

    def search(
        self,
        symbol: str,
        query: str,
        *,
        top_k: int = 5,
        doc_types: list[str] | None = None,
        include_episodic: bool = True,
    ) -> list[EvidenceChunk]:
        sym = symbol.upper()
        if not self._index.has_symbol(sym):
            self.ensure_index(sym)
        types = list(doc_types) if doc_types else None
        if types and not include_episodic:
            pass
        prefer = "prior" in query.lower() or "last analysis" in query.lower()
        return self.search_multi(
            sym,
            query,
            top_k=top_k,
            doc_types=types,
            prefer_episodic=prefer,
        )

    def search_multi(
        self,
        symbol: str,
        query: str,
        *,
        top_k: int = 5,
        doc_types: list[str] | None = None,
        prefer_episodic: bool = False,
    ) -> list[EvidenceChunk]:
        """多 query 变体召回 + rerank。"""
        sym = symbol.upper()
        if not self._index.has_symbol(sym):
            self.ensure_index(sym)

        seen: set[str] = set()
        candidates: list[EvidenceChunk] = []
        for q in expand_query(query):
            batch = self._index.search(
                sym,
                q,
                top_k=max(top_k, 5),
                doc_types=doc_types,
                prefer_episodic=prefer_episodic,
            )
            for c in batch:
                if c.doc_id in seen:
                    continue
                seen.add(c.doc_id)
                candidates.append(c)

        if not candidates:
            return self._index.search(sym, query, top_k=top_k, doc_types=doc_types, prefer_episodic=prefer_episodic)
        return rerank_chunks(query, candidates, top_k=top_k)

    def ingest_episodic_session(
        self,
        symbol: str,
        *,
        case_id: str,
        task: str,
        decision: dict[str, Any],
        risk_verdict: str | None,
        risk_reason: str | None,
        report: str | None,
        final_state: dict[str, Any] | None = None,
    ) -> EvidenceChunk:
        """分析结束后写入结构化 Episodic Memory 并持久化。"""
        sym = symbol.upper()
        if not self._index.has_symbol(sym):
            self._load_persisted(sym)

        chunk = build_episodic_chunk(
            sym,
            case_id=case_id,
            task=task,
            decision=decision,
            risk_verdict=risk_verdict,
            risk_reason=risk_reason,
            report=report,
            final_state=final_state,
        )
        existing = self._index.get_chunks(sym)
        merged = merge_chunk_lists(existing, [chunk])
        self._index.upsert(sym, merged, updated_at=self._now_iso())
        self._persist(sym)
        try:
            ingest_semantic_from_session(
                sym,
                report=report,
                decision=decision,
                case_id=case_id,
            )
            self.ensure_index(sym)
        except Exception:
            pass
        return chunk

    def ingest_analysis_report(self, symbol: str, report: str) -> None:
        """兼容旧接口：转为 episodic ingest 的简化路径。"""
        self.ingest_episodic_session(
            symbol,
            case_id="legacy_report",
            task="analysis report feedback",
            decision={"signal_type": "unknown", "confidence": 0},
            risk_verdict=None,
            risk_reason=None,
            report=report,
            final_state={},
        )

    def list_episodic(self, symbol: str, *, limit: int = 5) -> list[EvidenceChunk]:
        sym = symbol.upper()
        if not self._index.has_symbol(sym):
            self._load_persisted(sym)
        items = [c for c in self._index.get_chunks(sym) if is_episodic_chunk(c)]
        items.sort(key=lambda c: c.published_at or "", reverse=True)
        return items[:limit]

    def snapshot_to_state(
        self,
        chunks: list[EvidenceChunk],
        symbol: str | None = None,
    ) -> dict[str, Any]:
        flags = build_document_flags(chunks)
        if symbol:
            sym = symbol.upper()
            if self._index.has_symbol(sym):
                risk_hits = self._index.search(
                    sym,
                    "risk factors supply chain regulatory going concern",
                    top_k=6,
                )
                extra = extract_risk_flags(risk_hits)
                merged = sorted(set(flags.get("risk_flags", []) + extra))
                flags = {**flags, "risk_flags": merged}
        episodic = [c.to_dict() for c in chunks if is_episodic_chunk(c)]
        semantic = [c.to_dict() for c in chunks if c.doc_type == "semantic_fact"]
        return {
            "evidence_snapshot": [c.to_dict() for c in chunks],
            "episodic_memory": episodic,
            "semantic_memory": semantic,
            "document_flags": flags,
            "risk_flags": flags.get("risk_flags", []),
        }

    @classmethod
    def get_default(cls) -> EvidenceRetriever:
        global _default_retriever
        if _default_retriever is None:
            _default_retriever = cls()
        return _default_retriever


def chunks_for_risk_flags(chunks: list[dict[str, Any]]) -> list[str]:
    model_chunks = [
        EvidenceChunk(
            doc_id=c.get("doc_id", ""),
            text=c.get("text", ""),
            symbol=c.get("symbol", ""),
            doc_type=c.get("doc_type", ""),
            source=c.get("source", ""),
            title=c.get("title", ""),
            published_at=c.get("published_at"),
            source_url=c.get("source_url"),
            section=c.get("section"),
        )
        for c in chunks
    ]
    return extract_risk_flags(model_chunks)
