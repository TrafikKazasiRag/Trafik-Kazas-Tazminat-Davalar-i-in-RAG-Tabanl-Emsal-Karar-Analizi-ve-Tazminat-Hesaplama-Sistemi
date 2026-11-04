import json

import pytest

from trafikrag.adapters.lexical import bm25, pg_fts
from trafikrag.adapters.rerankers import bge_reranker
from trafikrag.adapters.vector_stores import memory
from trafikrag.domain.decision import Chunk, ScoredChunk
from trafikrag.evaluation import metrics, run_eval
from trafikrag.retrieval.fusion import rrf
from trafikrag.retrieval.retriever import Retriever


def _sc(chunk_id: str, score: float = 1.0, decision_id: str | None = None) -> ScoredChunk:
    return ScoredChunk(Chunk(chunk_id, decision_id or chunk_id, "hukum", chunk_id, {}), score)


class _KeywordEmbedder:
    """Metinde geçen anahtar sözcüğe göre 2 boyutlu vektör üretir."""

    def embed(self, texts):
        return [[1.0, 0.0] if "araç" in t else [0.0, 1.0] for t in texts]


def _retriever(mode="hybrid", reranker=None, top_k=3, top_n=None) -> Retriever:
    chunks = [
        Chunk("c1", "d1", "hukum", "araç sürücü kusur oranı", {}),
        Chunk("c2", "d2", "hukum", "maluliyet oranı hesaplanır", {}),
        Chunk("c3", "d3", "hukum", "araç kavşakta çarpmıştır", {}),
        Chunk("c4", "d4", "hukum", "tedavi giderleri", {}),
        Chunk("c5", "d5", "hukum", "bakıcı gideri", {}),
        Chunk("c6", "d6", "hukum", "destekten yoksun kalma", {}),
    ]
    embedder = _KeywordEmbedder()
    store = memory.build({})
    store.add(chunks, embedder.embed([c.text for c in chunks]))
    lexical = bm25.build({})
    lexical.add(chunks)
    return Retriever(embedder, store, lexical, reranker, mode=mode, top_k=top_k, top_n=top_n)


def test_rrf_rewards_agreement_between_rankings():
    fused = rrf([[_sc("a"), _sc("b"), _sc("c")], [_sc("b"), _sc("d")]])
    assert fused[0].chunk.id == "b"
    assert {s.chunk.id for s in fused} == {"a", "b", "c", "d"}
    assert fused[0].score == pytest.approx(1 / 62 + 1 / 61)


def test_rrf_top_k_and_invalid_k():
    assert len(rrf([[_sc("a"), _sc("b")], [_sc("c")]], top_k=2)) == 2
    with pytest.raises(ValueError):
        rrf([], k=0)
    assert rrf([]) == []


def test_retriever_modes():
    assert _retriever("vector").retrieve("araç")[0].chunk.id in {"c1", "c3"}
    assert _retriever("lexical").retrieve("maluliyet")[0].chunk.id == "c2"
    hybrid = [r.chunk.id for r in _retriever("hybrid").retrieve("araç kusur")]
    assert hybrid[0] == "c1"


def test_retriever_filters_and_empty_query():
    retriever = _retriever("hybrid")
    assert retriever.retrieve("   ") == []
    assert {r.chunk.id for r in retriever.retrieve("araç", {"decision_id": "d3"})} == {"c3"}


def test_retriever_validates_mode_and_lexical():
    with pytest.raises(ValueError):
        Retriever(_KeywordEmbedder(), memory.build({}), mode="bogus")
    with pytest.raises(ValueError):
        Retriever(_KeywordEmbedder(), memory.build({}), mode="hybrid")


def test_retriever_applies_reranker_and_top_n():
    class Reverse:
        def rerank(self, query, candidates, top_n):
            return list(reversed(candidates))[:top_n]

    plain = [r.chunk.id for r in _retriever("hybrid", top_k=3).retrieve("araç kusur")]
    reranked = [r.chunk.id for r in _retriever("hybrid", Reverse(), top_k=3, top_n=2).retrieve("araç kusur")]
    assert reranked == list(reversed(plain))[:2]
    assert len(_retriever("vector", top_k=5, top_n=2).retrieve("araç")) == 2


def test_bge_reranker_orders_by_model_score():
    class FakeModel:
        def compute_score(self, pairs, **kwargs):
            return [0.1, 0.9, 0.5]

    reranker = bge_reranker.BgeReranker(FakeModel())
    result = reranker.rerank("q", [_sc("a"), _sc("b"), _sc("c")], top_n=2)
    assert [r.chunk.id for r in result] == ["b", "c"]
    assert reranker.rerank("q", [], 3) == []


def test_bge_reranker_scalar_score_and_length_mismatch():
    class Scalar:
        def compute_score(self, pairs, **kwargs):
            return 0.7

    assert bge_reranker.BgeReranker(Scalar()).rerank("q", [_sc("a")], 1)[0].score == 0.7

    class Wrong:
        def compute_score(self, pairs, **kwargs):
            return [0.1]

    with pytest.raises(RuntimeError):
        bge_reranker.BgeReranker(Wrong()).rerank("q", [_sc("a"), _sc("b")], 2)


def test_pg_fts_query_builder_and_validation(monkeypatch):
    assert pg_fts.build_tsquery("madde 85, kusur!") == "madde or 85 or kusur"
    assert pg_fts.build_tsquery("or OR kusur") == "kusur"
    assert pg_fts.build_tsquery("   ") == ""
    assert pg_fts.PgFtsIndex("dsn").search("   ", 5) == []
    with pytest.raises(ValueError):
        pg_fts.PgFtsIndex("dsn", config="x'; DROP TABLE chunks;--")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        pg_fts.build({})


def test_metrics():
    ranked = ["a", "b", "c"]
    assert metrics.hit_rate(ranked, {"c"}, 3) == 1.0
    assert metrics.hit_rate(ranked, {"c"}, 2) == 0.0
    assert metrics.reciprocal_rank(ranked, {"b", "c"}) == 0.5
    assert metrics.reciprocal_rank(ranked, {"z"}) == 0.0
    assert metrics.ndcg(["a", "b"], {"a", "b"}, 2) == pytest.approx(1.0)
    assert metrics.ndcg(["x", "a"], {"a"}, 2) == pytest.approx(1 / 1.5849625007)
    assert metrics.ndcg(["a"], set(), 3) == 0.0
    assert metrics.mean([]) == 0.0


def test_run_eval_reports_metrics(tmp_path):
    questions = tmp_path / "q.jsonl"
    questions.write_text(
        json.dumps({"query": "maluliyet", "relevant_decision_ids": ["d2"]}) + "\n"
        + json.dumps({"query": "tedavi", "relevant_decision_ids": ["d9"]}) + "\n",
        encoding="utf-8",
    )
    report = run_eval.evaluate(_retriever("lexical"), run_eval.load_questions(questions), k=3)
    assert report["questions"] == 2
    assert report["hit_rate@3"] == 0.5
    assert report["mrr@3"] == 0.5


def test_run_eval_rejects_bad_question_file(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"query": "x"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        run_eval.load_questions(bad)


def test_index_chunks_reports_failing_batch_range():
    from trafikrag.adapters.embedders.fake import FakeEmbedder
    from trafikrag.ingestion.steps.index import index_chunks

    class Broken:
        def add(self, chunks):
            raise OSError("db down")

    chunks = [Chunk(f"c{i}", "d", "hukum", "t", {}) for i in range(3)]
    with pytest.raises(RuntimeError, match="0-2"):
        index_chunks(chunks, FakeEmbedder(4), memory.build({}), Broken(), batch_size=2)


def test_index_chunks_writes_to_both_stores_in_batches():
    from trafikrag.adapters.embedders.fake import FakeEmbedder
    from trafikrag.ingestion.steps.index import index_chunks

    chunks = [Chunk(f'c{i}', 'd', 'hukum', f'metin {i}', {}) for i in range(5)]
    store, lexical = memory.build({}), bm25.build({})
    assert index_chunks(chunks, FakeEmbedder(4), store, lexical, batch_size=2) == 5
    assert len(store.search([1.0] * 4, top_k=10)) == 5
    assert len(lexical.search('metin 3', top_k=10)) >= 1
    with pytest.raises(ValueError):
        index_chunks(chunks, FakeEmbedder(4), store, batch_size=0)

