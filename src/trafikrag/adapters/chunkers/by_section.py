"""Bölüm bazlı chunker (B sürümü). build(cfg) -> Chunker"""
from __future__ import annotations

from trafikrag.adapters.chunkers._common import base_metadata, tokens_to_words
from trafikrag.domain.decision import Chunk, Decision


def split_text(text: str, max_words: int) -> list[str]:
    """Satırları (paragrafları) bozmadan, max_words sınırını aşmayacak şekilde paketler."""
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    def flush() -> None:
        nonlocal current, current_words
        if current:
            chunks.append("\n".join(current))
            current, current_words = [], 0

    for paragraph in (p.strip() for p in text.split("\n")):
        if not paragraph:
            continue
        words = paragraph.split()
        if len(words) > max_words:  # tek paragraf bile sınırı aşıyor: zorla böl
            flush()
            for start in range(0, len(words), max_words):
                chunks.append(" ".join(words[start:start + max_words]))
            continue
        if current_words + len(words) > max_words:
            flush()
        current.append(paragraph)
        current_words += len(words)
    flush()
    return chunks


class BySectionChunker:
    def __init__(self, max_tokens: int = 400) -> None:
        self.max_words = tokens_to_words(max_tokens)

    def chunk(self, decision: Decision) -> list[Chunk]:
        result: list[Chunk] = []
        for section in decision.sections:
            for part, piece in enumerate(split_text(section.text, self.max_words)):
                result.append(
                    Chunk(
                        id=f"{decision.id}:{section.kind}:{part}",
                        decision_id=decision.id,
                        section_kind=section.kind,
                        text=piece,
                        metadata={**base_metadata(decision), "part": part},
                    )
                )
        return result


def build(cfg: dict) -> BySectionChunker:
    return BySectionChunker(max_tokens=cfg.get("max_tokens", 400))
