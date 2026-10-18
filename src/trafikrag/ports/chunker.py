from typing import Protocol

from trafikrag.domain.decision import Chunk, Decision


class Chunker(Protocol):
    def chunk(self, decision: Decision) -> list[Chunk]: ...
