"""Gerçek Postgres (pgvector) gerektirir: `docker compose up -d db` ve DATABASE_URL tanımlı olmalı."""
import os

import pytest

from trafikrag.adapters.vector_stores import pgvector
from trafikrag.domain.decision import Chunk

pytestmark = pytest.mark.integration

DIM = pgvector.EMBEDDING_DIM


def _vec(*head: float) -> list[float]:
    return list(head) + [0.0] * (DIM - len(head))


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
