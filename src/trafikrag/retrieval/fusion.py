"""Reciprocal Rank Fusion (RRF)."""
from trafikrag.domain.decision import ScoredChunk


def rrf(rankings: list[list[ScoredChunk]], k: int = 60, top_k: int | None = None) -> list[ScoredChunk]:
    """Her sıralamadaki yere göre 1 / (k + sıra) puanı toplar; skorlar karşılaştırılmaz, yalnızca sıralar kullanılır."""
    if k <= 0:
        raise ValueError("k pozitif olmalı")
    scores: dict[str, float] = {}
    chunks: dict[str, ScoredChunk] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item.chunk.id] = scores.get(item.chunk.id, 0.0) + 1.0 / (k + rank)
            chunks.setdefault(item.chunk.id, item)
    ordered = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    fused = [ScoredChunk(chunk=chunks[cid].chunk, score=scores[cid]) for cid in ordered]
    return fused if top_k is None else fused[:top_k]
