"""Sabit boyutlu chunker (A sürümü, baseline). build(cfg) -> Chunker"""
from __future__ import annotations

from trafikrag.adapters.chunkers._common import base_metadata, tokens_to_words
from trafikrag.domain.decision import Chunk, Decision


class FixedSizeChunker:
    def __init__(self, size_tokens: int = 400, overlap_tokens: int = 50) -> None:
        self.size = tokens_to_words(size_tokens)
        self.overlap = tokens_to_words(overlap_tokens)
        if self.overlap >= self.size:
            raise ValueError("overlap, chunk boyutundan küçük olmalı")

    def chunk(self, decision: Decision) -> list[Chunk]:
        # Bölüm bilgisini bilerek yok sayıyoruz: baseline bu
        words = " ".join(s.text for s in decision.sections).split()
        step = self.size - self.overlap
        result: list[Chunk] = []
        for index, start in enumerate(range(0, len(words), step)):
            result.append(
                Chunk(
                    id=f"{decision.id}:fixed:{index}",
                    decision_id=decision.id,
                    section_kind="mixed",
                    text=" ".join(words[start:start + self.size]),
                    metadata={**base_metadata(decision), "part": index},
                )
            )
            if start + self.size >= len(words):
                break
        return result


def build(cfg: dict) -> FixedSizeChunker:
    return FixedSizeChunker(
        size_tokens=cfg.get("size_tokens", 400),
        overlap_tokens=cfg.get("overlap_tokens", 50),
    )
