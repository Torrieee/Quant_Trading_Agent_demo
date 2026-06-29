"""检索评测：Recall@K、MRR 与消融实验。"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import yaml

from ..evidence.ingest import build_symbol_chunks
from ..evidence.models import EvidenceChunk
from ..evidence.query_expand import expand_query
from ..evidence.rerank import rerank_chunks
from ..evidence.store import HybridEvidenceIndex

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RETRIEVAL_EVALSET = PROJECT_ROOT / "evalsets" / "retrieval_v1.yaml"


def load_retrieval_evalset(path: Path | str) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"retrieval evalset 格式错误: {path}")
    return data


def _is_relevant(chunk: EvidenceChunk, case: dict[str, Any]) -> bool:
    doc_ids = case.get("relevant_doc_ids") or []
    if doc_ids and chunk.doc_id in doc_ids:
        return True
    keywords = [k.lower() for k in (case.get("relevant_keywords") or [])]
    if not keywords:
        return False
    text = chunk.text.lower()
    return all(kw in text for kw in keywords)


def recall_at_k(ranked: list[EvidenceChunk], case: dict[str, Any], k: int) -> float:
    top = ranked[:k]
    if not top:
        return 0.0
    hits = sum(1 for c in top if _is_relevant(c, case))
    total_relevant = max(1, len(case.get("relevant_doc_ids") or []) or 1)
    return min(1.0, hits / total_relevant)


def mrr(ranked: list[EvidenceChunk], case: dict[str, Any]) -> float:
    for i, chunk in enumerate(ranked, start=1):
        if _is_relevant(chunk, case):
            return 1.0 / i
    return 0.0


@contextmanager
def _search_env(
    *,
    mode: str,
    use_rerank: bool,
    use_query_expand: bool,
) -> Iterator[None]:
    prev = {
        "EVIDENCE_SEARCH_MODE": os.environ.get("EVIDENCE_SEARCH_MODE"),
        "EVIDENCE_RERANK_CROSS_ENCODER": os.environ.get("EVIDENCE_RERANK_CROSS_ENCODER"),
        "RETRIEVAL_EVAL_USE_EXPAND": os.environ.get("RETRIEVAL_EVAL_USE_EXPAND"),
    }
    os.environ["EVIDENCE_SEARCH_MODE"] = mode
    os.environ["EVIDENCE_RERANK_CROSS_ENCODER"] = "0"
    os.environ["RETRIEVAL_EVAL_USE_EXPAND"] = "1" if use_query_expand else "0"
    # rerank 由调用方控制，不依赖 cross-encoder
    yield
    for key, val in prev.items():
        if val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = val


def _search_variant(
    index: HybridEvidenceIndex,
    symbol: str,
    query: str,
    *,
    top_k: int,
    use_rerank: bool,
    use_query_expand: bool,
) -> list[EvidenceChunk]:
    queries = expand_query(query) if use_query_expand else [query]
    seen: set[str] = set()
    merged: list[EvidenceChunk] = []
    for q in queries:
        for chunk in index.search(symbol, q, top_k=top_k * 2):
            if chunk.doc_id in seen:
                continue
            seen.add(chunk.doc_id)
            merged.append(chunk)
    merged.sort(key=lambda c: float(c.score or 0.0), reverse=True)
    candidates = merged[: top_k * 2]
    if use_rerank:
        return rerank_chunks(query, candidates, top_k=top_k)
    return candidates[:top_k]


def run_retrieval_eval(
    path: Path | str | None = None,
    *,
    k: int = 5,
) -> dict[str, Any]:
    spec = load_retrieval_evalset(path or DEFAULT_RETRIEVAL_EVALSET)
    symbol = (spec.get("symbol") or "FIXTURE").upper()
    cases = spec.get("cases") or []

    chunks = build_symbol_chunks(symbol, stock_info={"symbol": symbol, "sector": "Tech"})
    for doc in spec.get("extra_docs") or []:
        text = doc.get("text", "")
        if not text:
            continue
        chunks.append(
            EvidenceChunk(
                doc_id=doc.get("doc_id", f"{symbol}_extra"),
                text=text,
                symbol=symbol,
                doc_type=doc.get("doc_type", "10-K"),
                source="eval_setup",
                title=doc.get("title", "Extra"),
            )
        )

    variants = [
        {"name": "tfidf", "mode": "tfidf", "rerank": False, "expand": False},
        {"name": "hybrid", "mode": "hybrid", "rerank": False, "expand": False},
        {"name": "hybrid+expand", "mode": "hybrid", "rerank": False, "expand": True},
        {"name": "hybrid+rerank", "mode": "hybrid", "rerank": True, "expand": True},
    ]

    ablation_rows: list[dict[str, Any]] = []
    case_details: list[dict[str, Any]] = []

    for variant in variants:
        recalls: list[float] = []
        mrrs: list[float] = []
        with _search_env(
            mode=variant["mode"],
            use_rerank=variant["rerank"],
            use_query_expand=variant["expand"],
        ):
            index = HybridEvidenceIndex()
            index.upsert(symbol, chunks)
            for case in cases:
                query = case["query"]
                ranked = _search_variant(
                    index,
                    symbol,
                    query,
                    top_k=k,
                    use_rerank=variant["rerank"],
                    use_query_expand=variant["expand"],
                )
                r = recall_at_k(ranked, case, k)
                m = mrr(ranked, case)
                recalls.append(r)
                mrrs.append(m)
                if variant["name"] == spec.get("primary_variant", "hybrid+rerank"):
                    case_details.append(
                        {
                            "name": case.get("name", query[:40]),
                            "query": query,
                            f"recall@{k}": round(r, 3),
                            "mrr": round(m, 3),
                            "top_doc_ids": [c.doc_id for c in ranked[:k]],
                        }
                    )

        n = max(len(recalls), 1)
        ablation_rows.append(
            {
                "variant": variant["name"],
                f"recall@{k}": round(sum(recalls) / n, 3),
                "mrr": round(sum(mrrs) / n, 3),
            }
        )

    benchmark = spec.get("benchmark") or {}
    primary = next(
        (r for r in ablation_rows if r["variant"] == spec.get("primary_variant", "hybrid+rerank")),
        ablation_rows[-1] if ablation_rows else {},
    )
    min_recall = float(benchmark.get("min_recall_at_k", 0.5))
    min_mrr = float(benchmark.get("min_mrr", 0.3))
    passed = (
        primary.get(f"recall@{k}", 0) >= min_recall
        and primary.get("mrr", 0) >= min_mrr
    )

    return {
        "evalset_id": spec.get("evalset_id", "retrieval_v1"),
        "symbol": symbol,
        "k": k,
        "ablation": ablation_rows,
        "cases": case_details,
        "benchmark": {
            "passed": passed,
            "min_recall_at_k": min_recall,
            "min_mrr": min_mrr,
            "primary_variant": spec.get("primary_variant", "hybrid+rerank"),
            "actual": primary,
        },
    }
