"""Gerçek Postgres (pgvector) gerektirir: `docker compose up -d db` ve DATABASE_URL tanımlı olmalı."""
import os

import pytest

from trafikrag.adapters.lexical import bm25, pg_fts
from trafikrag.adapters.vector_stores import pgvector
from trafikrag.domain.decision import Chunk

pytestmark = pytest.mark.integration

DIM = pgvector.EMBEDDING_DIM


def _vec(*head: float) -> list[float]:
    return [float(value) for value in head] + [0.0] * (DIM - len(head))


@pytest.fixture
def store():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        pytest.skip("DATABASE_URL tanımlı değil")
    store = pgvector.PgVectorStore(dsn)
    try:
        conn = store._connection()
    except Exception as exc:
        pytest.skip(f"Veritabanına bağlanılamadı: {exc}")
    conn.execute("DELETE FROM chunks WHERE id LIKE 'it_%'")
    yield store
    conn.execute("DELETE FROM chunks WHERE id LIKE 'it_%'")


def _mine(results):
    return [r.chunk.id for r in results if r.chunk.id.startswith("it_")]


def test_add_search_and_filters(store):
    store.add(
        [
            Chunk("it_1", "d1", "hukum", "a", {"court": "17. HD", "date": "2021-03-10"}),
            Chunk("it_2", "d2", "olay", "b", {"court": "17. HD", "date": "2022-06-01"}),
            Chunk("it_3", "d3", "hukum", "c", {"court": "4. HD", "date": "2020-01-15"}),
        ],
        [_vec(1, 0), _vec(0.9, 0.1), _vec(0, 1)],
    )
    assert _mine(store.search(_vec(1, 0), top_k=50)) == ["it_1", "it_2", "it_3"]
    assert _mine(store.search(_vec(1, 0), top_k=50, filters={"court": "4. HD"})) == ["it_3"]
    ranged = {"date_from": "2021-01-01", "date_to": "2021-12-31"}
    assert _mine(store.search(_vec(1, 0), top_k=50, filters=ranged)) == ["it_1"]


def test_topics_and_excluded_decisions_in_postgres(store):
    store.add(
        [
            Chunk("it_filter_1", "it_filter_d1", "hukum", "ölüm tazminatı", {"topics": ["it_topic_olum"]}),
            Chunk(
                "it_filter_2",
                "it_filter_d2",
                "hukum",
                "yaralanma tazminatı",
                {"topics": ["it_topic_yaralanma", "it_topic_hasar"]},
            ),
            Chunk("it_filter_3", "it_filter_d3", "hukum", "başka konu", {"topics": ["it_topic_diger"]}),
        ],
        [_vec(1, 0), _vec(0.9, 0.1), _vec(0, 1)],
    )
    topic_results = store.search(
        _vec(1, 0), top_k=50, filters={"topics": ["it_topic_olum", "it_topic_hasar"]}
    )
    assert _mine(topic_results) == ["it_filter_1", "it_filter_2"]

    excluded = store.search(
        _vec(1, 0),
        top_k=50,
        filters={
            "topics": ["it_topic_olum", "it_topic_hasar"],
            "exclude_decision_ids": ["it_filter_d1", "it_filter_d3"],
        },
    )
    assert _mine(excluded) == ["it_filter_2"]


def test_postgres_fts_and_bm25_turkish_case_folding(store):
    chunks = [
        Chunk("it_fts_1", "it_fts_d1", "gerekce", "Davacının maluliyet oranı hesaplanmıştır.", {}),
        Chunk("it_fts_2", "it_fts_d2", "hukum", "Araç sürücüsü kusurlu bulunmuştur.", {}),
        Chunk("it_fts_3", "it_fts_d3", "olay", "Kaza tutanağı düzenlenmiştir.", {}),
    ]
    fts = pg_fts.PgFtsIndex(os.environ["DATABASE_URL"])
    fts.add(chunks)
    lexical = bm25.build({})
    lexical.add(chunks)

    query = "MALULİYET ORANI"
    fts_results = fts.search(
        query,
        top_k=3,
        filters={"decision_id": ["it_fts_d1", "it_fts_d2", "it_fts_d3"]},
    )
    assert [r.chunk.id for r in fts_results] == ["it_fts_1"]
    assert [r.chunk.id for r in lexical.search(query, top_k=3)][0] == "it_fts_1"
