"""Karar, bölüm ve chunk veri modelleri. Hiçbir şeye bağımlı değildir."""
from dataclasses import dataclass, field


@dataclass
class Section:
    kind: str  # "olay" | "gerekce" | "hukum"
    text: str


@dataclass
class Decision:
    id: str
    court: str  # daire
    esas_no: str
    karar_no: str
    date: str  # ISO
    source_url: str
    sections: list[Section] = field(default_factory=list)


@dataclass
class Chunk:
    id: str
    decision_id: str
    section_kind: str
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float
