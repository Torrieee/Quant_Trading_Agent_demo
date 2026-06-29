"""Evidence 稠密向量：Hashing（默认）或 sentence-transformers（可选）。"""

from __future__ import annotations

import os
from typing import Protocol

import numpy as np

_backend: "EmbeddingBackend | None" = None


class EmbeddingBackend(Protocol):
    name: str

    def embed_documents(self, texts: list[str]) -> np.ndarray: ...

    def embed_query(self, text: str) -> np.ndarray: ...


class HashingEmbeddingBackend:
    """离线 Hashing 向量（sklearn，无额外模型下载）。"""

    name = "hashing"

    def __init__(self, *, n_features: int = 256) -> None:
        from sklearn.feature_extraction.text import HashingVectorizer

        self._vectorizer = HashingVectorizer(
            n_features=n_features,
            alternate_sign=False,
            norm="l2",
            lowercase=True,
            ngram_range=(1, 2),
        )

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        matrix = self._vectorizer.transform(texts)
        return matrix.toarray().astype(np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_documents([text])[0]


class SentenceTransformerBackend:
    """可选 sentence-transformers 后端（需 pip install sentence-transformers）。"""

    name = "sentence_transformers"

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers 未安装。请执行: pip install 'quant-research-agent[embedding]'"
            ) from exc
        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vectors, dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_documents([text])[0]


def embedding_backend_name() -> str:
    return os.environ.get("EVIDENCE_EMBEDDING_BACKEND", "hashing").strip().lower()


def embedding_model_name() -> str:
    return os.environ.get("EVIDENCE_EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip()


def embedding_dim() -> int:
    return int(os.environ.get("EVIDENCE_EMBEDDING_DIM", "256"))


def get_embedding_backend(*, force_new: bool = False) -> EmbeddingBackend:
    """懒加载 embedding 后端单例。"""
    global _backend
    if _backend is not None and not force_new:
        return _backend

    backend = embedding_backend_name()
    if backend in ("sentence_transformers", "st", "transformer"):
        _backend = SentenceTransformerBackend(embedding_model_name())
    else:
        _backend = HashingEmbeddingBackend(n_features=embedding_dim())
    return _backend


def reset_embedding_backend() -> None:
    global _backend
    _backend = None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0:
        return 0.0
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)
