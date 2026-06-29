"""Hybrid 证据索引：TF-IDF + Embedding 融合检索。"""

from __future__ import annotations

import datetime as dt
import math
import re
from collections import Counter

import numpy as np

from .config import hybrid_alpha, search_mode
from .embeddings import cosine_similarity, get_embedding_backend
from .memory import is_episodic_chunk
from .models import EvidenceChunk, SymbolIndex


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _parse_published_at(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d %H:%M UTC", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = dt.datetime.strptime(text[: len(fmt) + 4], fmt)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=dt.timezone.utc)
            return parsed
        except ValueError:
            continue
    return None


def _recency_multiplier(chunk: EvidenceChunk, *, half_life_days: float = 90.0) -> float:
    """Episodic 条目越新得分越高；披露文档按 filing 日期衰减。"""
    published = _parse_published_at(chunk.published_at)
    if published is None:
        return 1.0 if not is_episodic_chunk(chunk) else 1.1

    age_days = max(0.0, (dt.datetime.now(dt.timezone.utc) - published).total_seconds() / 86400.0)
    decay = math.exp(-0.693 * age_days / half_life_days)

    if is_episodic_chunk(chunk):
        return 1.0 + 0.35 * decay
    if chunk.source == "sec_edgar":
        return 0.85 + 0.15 * decay
    return 1.0


class HybridEvidenceIndex:
    """按 symbol 维护 TF-IDF + Embedding 混合检索索引。"""

    def __init__(self) -> None:
        self._indexes: dict[str, SymbolIndex] = {}
        self._lexical_vectors: dict[str, list[dict[str, float]]] = {}
        self._idf: dict[str, dict[str, float]] = {}
        self._dense_vectors: dict[str, np.ndarray] = {}

    def upsert(self, symbol: str, chunks: list[EvidenceChunk], *, updated_at: str | None = None) -> None:
        sym = symbol.upper()
        self._indexes[sym] = SymbolIndex(symbol=sym, chunks=list(chunks), updated_at=updated_at)
        self._build_index(sym)

    def get_chunks(self, symbol: str) -> list[EvidenceChunk]:
        idx = self._indexes.get(symbol.upper())
        return list(idx.chunks) if idx else []

    def _build_index(self, symbol: str) -> None:
        idx = self._indexes[symbol]
        docs = [_tokenize(c.text) for c in idx.chunks]
        n = len(docs)
        if n == 0:
            self._lexical_vectors[symbol] = []
            self._idf[symbol] = {}
            self._dense_vectors[symbol] = np.zeros((0, 0), dtype=np.float32)
            return

        df: Counter[str] = Counter()
        for tokens in docs:
            df.update(set(tokens))

        idf = {t: math.log((1 + n) / (1 + df[t])) + 1.0 for t in df}
        self._idf[symbol] = idf

        lexical_vectors: list[dict[str, float]] = []
        for tokens in docs:
            tf = Counter(tokens)
            total = sum(tf.values()) or 1
            vec = {t: (count / total) * idf.get(t, 1.0) for t, count in tf.items()}
            lexical_vectors.append(vec)
        self._lexical_vectors[symbol] = lexical_vectors

        mode = search_mode()
        if mode in ("hybrid", "embedding"):
            backend = get_embedding_backend()
            texts = [c.text for c in idx.chunks]
            self._dense_vectors[symbol] = backend.embed_documents(texts)
        else:
            self._dense_vectors[symbol] = np.zeros((n, 0), dtype=np.float32)

    @staticmethod
    def _cosine_sparse(a: dict[str, float], b: dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in set(a) | set(b))
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def _score_chunk(
        self,
        symbol: str,
        query: str,
        index: int,
        chunk: EvidenceChunk,
        *,
        prefer_episodic: bool,
    ) -> float:
        mode = search_mode()
        lexical = 0.0
        dense = 0.0

        q_tokens = _tokenize(query)
        if q_tokens:
            tf = Counter(q_tokens)
            total = sum(tf.values()) or 1
            idf = self._idf.get(symbol, {})
            q_vec = {t: (count / total) * idf.get(t, 1.0) for t, count in tf.items()}
            lexical_vectors = self._lexical_vectors.get(symbol, [])
            lexical = self._cosine_sparse(q_vec, lexical_vectors[index] if index < len(lexical_vectors) else {})

        dense_matrix = self._dense_vectors.get(symbol)
        if mode in ("hybrid", "embedding") and dense_matrix is not None and dense_matrix.size > 0:
            backend = get_embedding_backend()
            q_dense = backend.embed_query(query)
            if index < len(dense_matrix):
                dense = cosine_similarity(q_dense, dense_matrix[index])

        if mode == "embedding":
            base = dense
        elif mode == "hybrid":
            alpha = hybrid_alpha()
            base = alpha * dense + (1.0 - alpha) * lexical
        else:
            base = lexical

        mult = _recency_multiplier(chunk)
        if prefer_episodic and is_episodic_chunk(chunk):
            mult *= 1.25
        return base * mult

    def search(
        self,
        symbol: str,
        query: str,
        *,
        top_k: int = 5,
        doc_types: list[str] | None = None,
        prefer_episodic: bool = False,
    ) -> list[EvidenceChunk]:
        sym = symbol.upper()
        idx = self._indexes.get(sym)
        if not idx or not idx.chunks:
            return []

        if not query.strip():
            return idx.chunks[:top_k]

        scored: list[tuple[float, int]] = []
        for i, chunk in enumerate(idx.chunks):
            if doc_types and chunk.doc_type not in doc_types:
                continue
            score = self._score_chunk(sym, query, i, chunk, prefer_episodic=prefer_episodic)
            scored.append((score, i))

        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[EvidenceChunk] = []
        for score, i in scored[:top_k]:
            if score <= 0 and results:
                break
            c = idx.chunks[i]
            results.append(
                EvidenceChunk(
                    doc_id=c.doc_id,
                    text=c.text,
                    symbol=c.symbol,
                    doc_type=c.doc_type,
                    source=c.source,
                    title=c.title,
                    published_at=c.published_at,
                    source_url=c.source_url,
                    section=c.section,
                    score=round(score, 4),
                )
            )
        if not results and idx.chunks:
            return idx.chunks[:top_k]
        return results

    def has_symbol(self, symbol: str) -> bool:
        sym = symbol.upper()
        return sym in self._indexes and bool(self._indexes[sym].chunks)


# 向后兼容别名
TfidfEvidenceIndex = HybridEvidenceIndex
