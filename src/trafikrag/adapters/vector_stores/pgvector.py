"""pgvector VectorStore. build(cfg) -> VectorStore

Bağlantı adresi ortam değişkeninden okunur (varsayılan: DATABASE_URL).
Desteklenen filtreler: section_kind, decision_id, date_from / date_to (ISO tarih);
diğer anahtarlar (örn. court, topics) metadata alanıyla eşleştirilir; alan liste ise
(topics) değerin listede bulunması yeterlidir, filtre değeri liste ise herhangi biri yeterlidir.
"""
import json
import os
import warnings

from trafikrag.domain.decision import Chunk, ScoredChunk

EMBEDDING_DIM = 1024  # bge_m3 boyutu

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    section_kind TEXT NOT NULL,
    text TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{{}}',
    embedding vector({EMBEDDING_DIM})
);
CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS ix_chunks_metadata_gin
    ON chunks USING gin (metadata);
"""

# pgvector >= 0.8.0: filtre HNSW taramasından sonra uygulandığı için az sonuç dönmesini önler
_ITERATIVE_SCAN = ("relaxed_order", "strict_order", "off")

_COLUMN_FILTERS = ("section_kind", "decision_id")


def _build_where(filters: dict | None) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    for key, value in (filters or {}).items():
        if value is None:
            continue
        if key in _COLUMN_FILTERS:
            if isinstance(value, (list, tuple, set)):
                clauses.append(f"{key} = ANY(%s)")
                params.append(list(value))
            else:
                clauses.append(f"{key} = %s")
                params.append(value)
        elif key == "date_from":
            clauses.append("metadata->>'date' >= %s")
            params.append(str(value))
        elif key == "date_to":
            clauses.append("metadata->>'date' <= %s")
            params.append(str(value))
        else:
            # Skaler alan eşitliği ya da liste değerli alanın (örn. topics) içermesi;
            # içerme sorgusu (@>) GIN indeksini kullanır.
            values = [str(v) for v in value] if isinstance(value, (list, tuple, set)) else [str(value)]
            if not values:
                clauses.append("FALSE")
                continue
            parts = ["metadata->>%s = ANY(%s)"]
            params.extend([key, values])
            for v in values:
                parts.append("metadata @> %s::jsonb")
                params.append(json.dumps({key: [v]}, ensure_ascii=False))
            clauses.append("(" + " OR ".join(parts) + ")")
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


class PgVectorStore:
    def __init__(self, dsn: str, iterative_scan: str = "relaxed_order") -> None:
        if iterative_scan not in _ITERATIVE_SCAN:
            raise ValueError(f"iterative_scan {_ITERATIVE_SCAN} değerlerinden biri olmalı")
        self._dsn = dsn
        self._iterative_scan = iterative_scan
        self._conn = None

    def _connection(self):
        if self._conn is None or self._conn.closed:
            import psycopg
            from pgvector.psycopg import register_vector

            conn = psycopg.connect(self._dsn, autocommit=True)
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            register_vector(conn)
            conn.execute(_SCHEMA)
            try:
                conn.execute(f"SET hnsw.iterative_scan = {self._iterative_scan}")
            except psycopg.Error:
                warnings.warn("hnsw.iterative_scan desteklenmiyor (pgvector >= 0.8.0 gerekir)")
            self._conn = conn
        return self._conn

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError(f"{len(chunks)} chunk için {len(vectors)} vektör verildi")
        if not chunks:
            return
        for chunk, vector in zip(chunks, vectors):
            if len(vector) != EMBEDDING_DIM:
                raise ValueError(
                    f"Vektör boyutu {len(vector)}; beklenen {EMBEDDING_DIM} (chunk: {chunk.id})"
                )
        rows = [
            (
                chunk.id,
                chunk.decision_id,
                chunk.section_kind,
                chunk.text,
                json.dumps(chunk.metadata, ensure_ascii=False),
                vector,
            )
            for chunk, vector in zip(chunks, vectors)
        ]
        with self._connection().cursor() as cur:
            cur.executemany(
                """
                INSERT INTO chunks (id, decision_id, section_kind, text, metadata, embedding)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::vector)
                ON CONFLICT (id) DO UPDATE SET
                    decision_id = EXCLUDED.decision_id,
                    section_kind = EXCLUDED.section_kind,
                    text = EXCLUDED.text,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding
                """,
                rows,
            )

    def search(
        self, vector: list[float], top_k: int, filters: dict | None = None
    ) -> list[ScoredChunk]:
        if top_k <= 0:
            return []
        if len(vector) != EMBEDDING_DIM:
            raise ValueError(f"Sorgu vektörü boyutu {len(vector)}; beklenen {EMBEDDING_DIM}")
        where, params = _build_where(filters)
        where = (where + " AND embedding IS NOT NULL") if where else " WHERE embedding IS NOT NULL"
        sql = (
            "SELECT id, decision_id, section_kind, text, metadata, "
            "1 - (embedding <=> %s::vector) AS score FROM chunks"
            f"{where} ORDER BY embedding <=> %s::vector LIMIT %s"
        )
        with self._connection().cursor() as cur:
            cur.execute(sql, [vector, *params, vector, top_k])
            rows = cur.fetchall()
        return [
            ScoredChunk(
                chunk=Chunk(
                    id=row[0],
                    decision_id=row[1],
                    section_kind=row[2],
                    text=row[3],
                    metadata=row[4] or {},
                ),
                score=float(row[5]),
            )
            for row in rows
        ]


def build(cfg: dict) -> PgVectorStore:
    env_name = cfg.get("dsn_env", "DATABASE_URL")
    dsn = os.environ.get(env_name)
    if not dsn:
        raise RuntimeError(f"{env_name} ortam değişkeni tanımlı değil")
    return PgVectorStore(dsn, iterative_scan=cfg.get("iterative_scan", "relaxed_order"))
