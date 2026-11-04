"""PostgreSQL tam metin arama. build(cfg) -> LexicalIndex

pgvector deposuyla aynı `chunks` tablosunu paylaşır (tsv kolonu ve GIN indeksi eklenir);
aynı chunk'ı iki yerden de eklemek güvenlidir, embedding kolonuna dokunulmaz.
Filtreler pgvector deposuyla aynıdır. Bağlantı adresi DATABASE_URL ortam değişkeninden okunur.
"""
import json
import os
import re

from trafikrag.adapters.vector_stores.pgvector import _SCHEMA, _build_where
from trafikrag.domain.decision import Chunk, ScoredChunk

_WORD = re.compile(r"\w+")
# Karar numaralarıyla da aranabilsin diye indekse eklenen metadata alanları
_TSV_SCHEMA = """
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS tsv tsvector GENERATED ALWAYS AS (
    to_tsvector(
        'turkish',
        text || ' ' || coalesce(metadata->>'esas_no', '') || ' ' || coalesce(metadata->>'karar_no', '')
    )
) STORED;
CREATE INDEX IF NOT EXISTS ix_chunks_tsv ON chunks USING gin (tsv);
"""


def build_tsquery(query: str) -> str:
    """Sorgudaki sözcükleri OR ile birleştirir (doğal dil sorguları AND ile neredeyse hiç eşleşmez)."""
    return " | ".join(_WORD.findall(query))


class PgFtsIndex:
    def __init__(self, dsn: str, config: str = "turkish") -> None:
        if not re.fullmatch(r"[a-z_]+", config):
            raise ValueError(f"Geçersiz metin arama yapılandırması: {config!r}")
        self._dsn = dsn
        self._config = config
        self._conn = None

    def _connection(self):
        if self._conn is None or self._conn.closed:
            import psycopg

            conn = psycopg.connect(self._dsn, autocommit=True)
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(_SCHEMA)
            conn.execute(_TSV_SCHEMA)
            self._conn = conn
        return self._conn

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        rows = [
            (c.id, c.decision_id, c.section_kind, c.text, json.dumps(c.metadata, ensure_ascii=False))
            for c in chunks
        ]
        with self._connection().cursor() as cur:
            cur.executemany(
                """
                INSERT INTO chunks (id, decision_id, section_kind, text, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    decision_id = EXCLUDED.decision_id,
                    section_kind = EXCLUDED.section_kind,
                    text = EXCLUDED.text,
                    metadata = EXCLUDED.metadata
                """,
                rows,
            )

    def search(self, query: str, top_k: int, filters: dict | None = None) -> list[ScoredChunk]:
        tsquery = build_tsquery(query)
        if top_k <= 0 or not tsquery:
            return []
        where, params = _build_where(filters)
        match = f"tsv @@ q.query{' AND' + where[len(' WHERE'):] if where else ''}"
        sql = (
            "SELECT id, decision_id, section_kind, text, metadata, ts_rank_cd(tsv, q.query) AS score "
            f"FROM chunks, (SELECT to_tsquery('{self._config}', %s) AS query) AS q "
            f"WHERE {match} ORDER BY score DESC, id LIMIT %s"
        )
        with self._connection().cursor() as cur:
            cur.execute(sql, [tsquery, *params, top_k])
            rows = cur.fetchall()
        return [
            ScoredChunk(
                chunk=Chunk(
                    id=row[0], decision_id=row[1], section_kind=row[2], text=row[3], metadata=row[4] or {}
                ),
                score=float(row[5]),
            )
            for row in rows
        ]


def build(cfg: dict) -> PgFtsIndex:
    env_name = cfg.get("dsn_env", "DATABASE_URL")
    dsn = os.environ.get(env_name)
    if not dsn:
        raise RuntimeError(f"{env_name} ortam değişkeni tanımlı değil")
    return PgFtsIndex(dsn, config=cfg.get("config", "turkish"))
