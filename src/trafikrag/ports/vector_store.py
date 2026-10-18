from typing import Protocol

from trafikrag.domain.decision import Chunk, ScoredChunk


class VectorStore(Protocol):
    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...

    def search(self, vector: list[float], top_k: int, filters: dict | None = None) -> list[ScoredChunk]: ...
