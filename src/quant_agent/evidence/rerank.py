"""检索结果重排序（lexical boost + 可选 cross-encoder）。"""

from __future__ import annotations

import os
import re

from .models import EvidenceChunk

_reranker = None


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def lexical_overlap_score(query: str, doc_text: str) -> float:
    q = _token_set(query)
    d = _token_set(doc_text)
    if not q or not d:
        return 0.0
    return len(q & d) / len(q)


def rerank_chunks(
    query: str,
    chunks: list[EvidenceChunk],
    *,
    top_k: int | None = None,
) -> list[EvidenceChunk]:
    """对候选 chunk 二次打分；默认融合初排 score 与词重叠。"""
    if not chunks:
        return []

    use_ce = os.environ.get("EVIDENCE_RERANK_CROSS_ENCODER", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    ce_scores: dict[str, float] = {}
    if use_ce:
        ce_scores = _cross_encoder_scores(query, chunks)

    rescored: list[tuple[float, EvidenceChunk]] = []
    for c in chunks:
        base = float(c.score or 0.0)
        overlap = lexical_overlap_score(query, c.text)
        ce = ce_scores.get(c.doc_id, 0.0)
        if use_ce and ce > 0:
            final = 0.5 * ce + 0.3 * base + 0.2 * overlap
        else:
            final = 0.45 * base + 0.55 * overlap
        rescored.append(
            (
                final,
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
                    score=round(final, 4),
                ),
            )
        )

    rescored.sort(key=lambda x: x[0], reverse=True)
    out = [c for _, c in rescored]
    if top_k is not None:
        return out[:top_k]
    return out


def _cross_encoder_scores(query: str, chunks: list[EvidenceChunk]) -> dict[str, float]:
    global _reranker
    try:
        if _reranker is None:
            from sentence_transformers import CrossEncoder

            model_name = os.environ.get(
                "EVIDENCE_RERANK_MODEL",
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
            )
            _reranker = CrossEncoder(model_name)
        pairs = [(query, c.text[:512]) for c in chunks]
        raw = _reranker.predict(pairs)
        return {c.doc_id: float(s) for c, s in zip(chunks, raw)}
    except Exception:
        return {}
