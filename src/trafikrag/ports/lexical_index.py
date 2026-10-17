from typing import Protocol

from trafikrag.domain.decision import Chunk, ScoredChunk


class LexicalIndex(Protocol):
    def add(self, chunks: list[Chunk]) -> None: ...

    def search(self, query: str, top_k: int, filters: dict | None = None) -> list[ScoredChunk]: ...
