"""Hibrit arama, metadata filtresi, birleştirme.

Arama zinciri: sorgu -> (vektör | sözcük | hibrit RRF) -> opsiyonel reranker.
"""
from trafikrag.domain.decision import ScoredChunk
from trafikrag.ports.embedder import Embedder
from trafikrag.ports.lexical_index import LexicalIndex
from trafikrag.ports.reranker import Reranker
from trafikrag.ports.vector_store import VectorStore
from trafikrag.retrieval.fusion import rrf

MODES = ("vector", "lexical", "hybrid")


class Retriever:
    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        lexical: LexicalIndex | None = None,
        reranker: Reranker | None = None,
        mode: str = "vector",
        top_k: int = 8,
        top_n: int | None = None,
        rrf_k: int = 60,
    ) -> None:
        if mode not in MODES:
            raise ValueError(f"mode {MODES} değerlerinden biri olmalı: {mode!r}")
        if mode != "vector" and lexical is None:
            raise ValueError(f"{mode} modu için lexical indeks gerekli")
        self._embedder = embedder
        self._vector_store = vector_store
        self._lexical = lexical
        self._reranker = reranker
        self._mode = mode
        self._top_k = top_k
        self._top_n = top_n
        self._rrf_k = rrf_k

    def retrieve(self, query: str, filters: dict | None = None) -> list[ScoredChunk]:
        if not query.strip():
            return []
        rankings: list[list[ScoredChunk]] = []
        if self._mode in ("vector", "hybrid"):
            vector = self._embedder.embed([query])[0]
            rankings.append(self._vector_store.search(vector, self._top_k, filters))
        if self._mode in ("lexical", "hybrid"):
            rankings.append(self._lexical.search(query, self._top_k, filters))

        candidates = rankings[0] if len(rankings) == 1 else rrf(rankings, self._rrf_k, self._top_k)
        if self._reranker is not None:
            return self._reranker.rerank(query, candidates, self._top_n or self._top_k)
        return candidates[: self._top_n] if self._top_n else candidates


def build_retriever(container: dict) -> Retriever:
    """bootstrap.build_container çıktısından Retriever kurar."""
    retrieval = container["config"].get("retrieval", {})
    return Retriever(
        embedder=container["embedder"],
        vector_store=container["vector_store"],
        lexical=container.get("lexical"),
        reranker=container.get("reranker"),
        mode=retrieval.get("mode", "vector"),
        top_k=retrieval.get("top_k", 8),
        top_n=container["config"].get("reranker", {}).get("top_n"),
        rrf_k=retrieval.get("rrf_k", 60),
    )
