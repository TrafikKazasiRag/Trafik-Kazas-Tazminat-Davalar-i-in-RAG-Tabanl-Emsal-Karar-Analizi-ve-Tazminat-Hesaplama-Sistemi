"""BM25 LexicalIndex. build(cfg) -> LexicalIndex

Geçici bellek içi sürüm; kalıcı sürüm pg_fts.py olacak.
"""
import re

from rank_bm25 import BM25Okapi

from trafikrag.domain.decision import Chunk, ScoredChunk

_TOKEN = re.compile(r"\d+/\d+|\w+")
_NUMBER_PAIR = re.compile(r"\d+/\d+")
# Karar numaralarıyla da aranabilsin diye indekse eklenen metadata alanları
_ID_FIELDS = ("esas_no", "karar_no")


def _tr_lower(text: str) -> str:
    # Python'un lower()'ı "İ" ve "I" harflerini Türkçe'ye göre çevirmez
    return text.replace("İ", "i").replace("I", "ı").lower()


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for token in _TOKEN.findall(_tr_lower(text)):
        tokens.append(token)
        # "2019/1234" hem bütün hem de "2019", "1234" olarak aranabilsin
        if _NUMBER_PAIR.fullmatch(token):
            tokens.extend(token.split("/"))
    return tokens


def _document_tokens(chunk: Chunk) -> list[str]:
    parts = [chunk.text] + [str(chunk.metadata.get(f, "")) for f in _ID_FIELDS]
    return tokenize(" ".join(parts))


def _matches(chunk: Chunk, filters: dict) -> bool:
    for key, expected in filters.items():
        if key == "section_kind":
            actual = chunk.section_kind
        elif key == "decision_id":
            actual = chunk.decision_id
        else:
            actual = chunk.metadata.get(key)
        if isinstance(expected, (list, tuple, set)):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


class Bm25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b
        self._chunks: dict[str, Chunk] = {}
        self._tokens: dict[str, list[str]] = {}
        self._order: list[str] = []
        self._bm25: BM25Okapi | None = None

    def add(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            if chunk.id not in self._chunks:
                self._order.append(chunk.id)
            self._chunks[chunk.id] = chunk
            self._tokens[chunk.id] = _document_tokens(chunk)
        self._bm25 = None  # bir sonraki aramada yeniden kurulur

    def search(
        self, query: str, top_k: int, filters: dict | None = None
    ) -> list[ScoredChunk]:
        if top_k <= 0 or not self._order:
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        if self._bm25 is None:
            corpus = [self._tokens[cid] for cid in self._order]
            self._bm25 = BM25Okapi(corpus, k1=self._k1, b=self._b)
        scores = self._bm25.get_scores(query_tokens)

        results = []
        for chunk_id, score in zip(self._order, scores):
            chunk = self._chunks[chunk_id]
            if score > 0 and (not filters or _matches(chunk, filters)):
                results.append(ScoredChunk(chunk=chunk, score=float(score)))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


def build(cfg: dict) -> Bm25Index:
    return Bm25Index(k1=cfg.get("k1", 1.5), b=cfg.get("b", 0.75))
