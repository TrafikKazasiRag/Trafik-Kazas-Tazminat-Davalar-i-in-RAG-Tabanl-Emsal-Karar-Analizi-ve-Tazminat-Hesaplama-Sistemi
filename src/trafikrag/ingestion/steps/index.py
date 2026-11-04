"""index.py: Kararları ve chunk'ları indeksleme, metadata ve konu etiketleme adımı."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trafikrag.domain.decision import Chunk, Decision
from trafikrag.ports.embedder import Embedder
from trafikrag.ports.lexical_index import LexicalIndex
from trafikrag.ports.vector_store import VectorStore
from trafikrag.retrieval.topics import classify_topic


def extract_decision_topics(decision: Decision) -> list[str]:
    """Karar düzeyindeki konuyu tespit eder ve liste (topics) olarak döndürür.

    Not: şimdilik tek etiket, classify_topic sonucu listeye sarılıyor.
    """
    topic = classify_topic(decision)
    return [topic] if topic else ["diger"]


def build_chunk_metadata(decision: Decision, section_kind: str) -> dict[str, Any]:
    """Her chunk için karar düzeyindeki 'topics' etiketini barındıran metadata sözlüğü üretir."""
    topics = extract_decision_topics(decision)
    return {
        "decision_id": decision.id,
        "court": decision.court,
        "date": decision.date,
        "section_kind": section_kind,
        "topics": topics,
    }


def index_decision(decision: Decision) -> list[dict[str, Any]]:
    """Kararın bölümlerini chunk verisi ve zenginleştirilmiş metadata ile hazırlar."""
    indexed_chunks = []
    for section in decision.sections:
        indexed_chunks.append({
            "text": section.text,
            "metadata": build_chunk_metadata(decision, section.kind),
        })
    return indexed_chunks


def index_chunks(
    chunks: list[Chunk],
    embedder: Embedder,
    vector_store: VectorStore,
    lexical: LexicalIndex | None = None,
    batch_size: int = 64,
) -> int:
    """Chunk'ları gömüp vektör deposuna (ve varsa sözcük indeksine) yazar; yazılan chunk sayısını döner.

    Aynı id tekrar yazılırsa depolar günceller, yani adım tekrar çalıştırılabilir (idempotent).
    """
    if batch_size <= 0:
        raise ValueError("batch_size pozitif olmalı")
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        vector_store.add(batch, embedder.embed([chunk.text for chunk in batch]))
        if lexical is not None:
            lexical.add(batch)
    return len(chunks)


def write_decisions_jsonl(decisions: list[Decision], output_path: Path) -> Path:
    """Kararları ve konu etiketlerini JSONL formatında diske yazar (idempotent)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for dec in decisions:
            topics = extract_decision_topics(dec)
            dec_dict = {
                "id": dec.id,
                "court": dec.court,
                "esas_no": dec.esas_no,
                "karar_no": dec.karar_no,
                "date": dec.date,
                "source_url": dec.source_url,
                "topics": topics,
                "sections": [{"kind": s.kind, "text": s.text} for s in dec.sections],
            }
            f.write(json.dumps(dec_dict, ensure_ascii=False) + "\n")
    return output_path