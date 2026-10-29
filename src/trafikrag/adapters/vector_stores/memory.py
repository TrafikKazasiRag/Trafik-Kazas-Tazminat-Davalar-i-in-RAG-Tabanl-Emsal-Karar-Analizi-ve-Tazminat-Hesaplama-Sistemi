"""Bellek içi VectorStore (DB gerektirmez; test ve yerel deneme için).

build(cfg) -> VectorStore. Filtre kuralları pgvector.py ile aynıdır.
"""
import math

from trafikrag.domain.decision import Chunk, ScoredChunk


def _matches(chunk: Chunk, filters: dict | None) -> bool:
    for key, expected in (filters or {}).items():
        if expected is None:
            continue
        date = str(chunk.metadata.get("date", ""))
        if key == "date_from":
            if not date or date < str(expected):
                return False
            continue
        if key == "date_to":
            if not date or date > str(expected):
                return False
            continue
        if key == "section_kind":
            actual = chunk.section_kind
        elif key == "decision_id":
            actual = chunk.decision_id
        else:
            actual = chunk.metadata.get(key)
        if isinstance(expected, (list, tuple, set)):
            if str(actual) not in {str(v) for v in expected}:
                return False
        elif str(actual) != str(expected):
            return False
    return True


def _cosine(a: list[float], b: list[float]) -> float:
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / norm if norm else 0.0


class MemoryVectorStore:
    def __init__(self) -> None:
        self._items: dict[str, tuple[Chunk, list[float]]] = {}

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError(f"{len(chunks)} chunk için {len(vectors)} vektör verildi")
        for chunk, vector in zip(chunks, vectors):
            self._items[chunk.id] = (chunk, list(vector))

    def search(
        self, vector: list[float], top_k: int, filters: dict | None = None
    ) -> list[ScoredChunk]:
        if top_k <= 0:
            return []
        scored = [
            ScoredChunk(chunk=chunk, score=_cosine(vector, stored))
            for chunk, stored in self._items.values()
            if _matches(chunk, filters)
        ]
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:top_k]


def build(cfg: dict) -> MemoryVectorStore:
    return MemoryVectorStore()
