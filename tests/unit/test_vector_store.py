import pytest

from trafikrag.adapters.vector_stores import memory, pgvector
from trafikrag.domain.decision import Chunk


def _store():
    store = memory.build({})
    store.add(
        [
            Chunk("c1", "d1", "hukum", "a", {"court": "17. HD", "date": "2021-03-10"}),
            Chunk("c2", "d2", "olay", "b", {"court": "17. HD", "date": "2022-06-01"}),
            Chunk("c3", "d3", "hukum", "c", {"court": "4. HD", "date": "2020-01-15"}),
        ],
        [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]],
    )
    return store


def test_search_returns_closest_first():
    results = _store().search([1.0, 0.0], top_k=3)
    assert [r.chunk.id for r in results] == ["c1", "c2", "c3"]
    assert results[0].score > results[1].score > results[2].score


def test_top_k_limits_results():
    assert len(_store().search([1.0, 0.0], top_k=2)) == 2


def test_court_filter():
    results = _store().search([1.0, 0.0], top_k=5, filters={"court": "4. HD"})
    assert [r.chunk.id for r in results] == ["c3"]


def test_date_range_filter():
    results = _store().search(
        [1.0, 0.0], top_k=5, filters={"date_from": "2021-01-01", "date_to": "2021-12-31"}
    )
    assert [r.chunk.id for r in results] == ["c1"]


def test_section_kind_filter():
    results = _store().search([1.0, 0.0], top_k=5, filters={"section_kind": "olay"})
    assert [r.chunk.id for r in results] == ["c2"]


def test_add_same_id_replaces():
    store = _store()
    store.add([Chunk("c1", "d1", "hukum", "yeni", {})], [[0.0, 1.0]])
    results = store.search([0.0, 1.0], top_k=5)
    assert sum(r.chunk.id == "c1" for r in results) == 1


def test_add_length_mismatch_raises():
    with pytest.raises(ValueError):
        memory.build({}).add([Chunk("x", "d", "olay", "t", {})], [])


def test_pg_where_clause_builds_parameters():
    where, params = pgvector._build_where(
        {"court": "17. HD", "date_from": "2021-01-01", "section_kind": "hukum"}
    )
    assert "metadata->>%s = %s" in where
    assert "metadata->>'date' >= %s" in where
    assert "section_kind = %s" in where
    assert params == ["court", "17. HD", "2021-01-01", "hukum"]
    assert pgvector._build_where(None) == ("", [])


def test_pg_add_validates_dimension():
    store = pgvector.PgVectorStore("postgresql://unused")
    with pytest.raises(ValueError):
        store.add([Chunk("x", "d", "olay", "t", {})], [[1.0, 2.0]])


def test_pg_build_requires_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        pgvector.build({})
