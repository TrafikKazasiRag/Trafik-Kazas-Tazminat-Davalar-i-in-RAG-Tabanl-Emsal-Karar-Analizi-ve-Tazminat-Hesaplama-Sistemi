from typing import Protocol

from trafikrag.domain.decision import ScoredChunk


class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[ScoredChunk], top_n: int) -> list[ScoredChunk]: ...
