"""bge-reranker-v2-m3. build(cfg) -> Reranker"""
from typing import Any

from trafikrag.domain.decision import ScoredChunk


def _load_model(model_name: str, use_fp16: bool) -> Any:
    from FlagEmbedding import FlagReranker

    return FlagReranker(model_name, use_fp16=use_fp16)


class BgeReranker:
    def __init__(self, model: Any, batch_size: int = 32, max_length: int = 1024) -> None:
        self._model = model
        self._batch_size = batch_size
        self._max_length = max_length

    def rerank(self, query: str, candidates: list[ScoredChunk], top_n: int) -> list[ScoredChunk]:
        if not candidates or top_n <= 0:
            return []
        pairs = [[query, candidate.chunk.text] for candidate in candidates]
        scores = self._model.compute_score(
            pairs, batch_size=self._batch_size, max_length=self._max_length, normalize=True
        )
        if not isinstance(scores, (list, tuple)):  # tek aday için skaler döner
            scores = [scores]
        if len(scores) != len(candidates):
            raise RuntimeError(f"{len(candidates)} aday için {len(scores)} skor döndü")
        reranked = [
            ScoredChunk(chunk=candidate.chunk, score=float(score))
            for candidate, score in zip(candidates, scores)
        ]
        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked[:top_n]


def build(cfg: dict) -> BgeReranker:
    return BgeReranker(
        model=_load_model(cfg.get("model_name", "BAAI/bge-reranker-v2-m3"), cfg.get("use_fp16", False)),
        batch_size=cfg.get("batch_size", 32),
        max_length=cfg.get("max_length", 1024),
    )
