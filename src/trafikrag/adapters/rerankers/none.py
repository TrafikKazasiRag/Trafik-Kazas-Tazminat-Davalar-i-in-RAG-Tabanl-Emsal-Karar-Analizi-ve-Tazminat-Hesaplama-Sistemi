"""Reranker yok: adayları olduğu gibi keser."""
from trafikrag.domain.decision import ScoredChunk


class NoReranker:
    def rerank(self, query: str, candidates: list[ScoredChunk], top_n: int) -> list[ScoredChunk]:
        return candidates[:top_n]


def build(cfg: dict) -> NoReranker:
    return NoReranker()
