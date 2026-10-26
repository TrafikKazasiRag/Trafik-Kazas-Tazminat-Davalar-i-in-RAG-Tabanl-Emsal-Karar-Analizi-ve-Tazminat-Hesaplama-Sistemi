"""3. Adım (dedupe): Mükerrer kararları tespit eder ve en eksiksiz olan tek kaydı tutar.

Kurallar:
- Aynı Esas No + Karar No ikilisine sahip kayıtlardan metni daha eksiksiz (uzun/bölümlü) olan tutulur.
- Künye numarası çıkarılamayan veya farklı yazılan kararlarda normalleştirilmiş metin SHA-256 hash'i
  aynı olanlardan yalnızca biri tutulur.
- Adım idempotent'tir.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from trafikrag.ingestion.steps.parse_decision import extract_metadata, split_sections

_WHITESPACE_RE = re.compile(r"\s+")


def _normalized_hash(text: str) -> str:
    """Boşluk ve büyük/küçük harf farklarından arındırılmış metin SHA-256 özeti."""
    compact = _WHITESPACE_RE.sub(" ", text).strip().lower()
    return hashlib.sha256(compact.encode("utf-8")).hexdigest()


def _completeness_score(text: str) -> tuple[int, int]:
    """Kararın ne kadar eksiksiz olduğunu ölçer: (bölüm sayısı, temiz metin uzunluğu)."""
    sections = split_sections(text)
    clean_len = len(_WHITESPACE_RE.sub(" ", text).strip())
    return (len(sections), clean_len)


def _dedupe_key(text: str) -> str:
    """Esas ve Karar numarası varsa künye anahtarını, yoksa metin hash'ini döndürür."""
    meta = extract_metadata(text)
    esas = meta.get("esas_no", "").strip()
    karar = meta.get("karar_no", "").strip()
    if esas and karar:
        return f"ek:{esas}|{karar}"
    return f"hash:{_normalized_hash(text)}"


def dedupe_decisions(records: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """(karar_id, metin) çiftlerinden mükerrer olanları ayıklar, en eksiksiz olanı korur.

    Sıralamayı bozmadan (deterministik olarak) tekilleştirilmiş listeyi döndürür.
    """
    best_by_key: dict[str, tuple[str, str]] = {}
    best_by_hash: dict[str, str] = {}  # hash -> key eşleşmesi

    for doc_id, text in records:
        if not text or not text.strip():
            continue

        key = _dedupe_key(text)
        text_hash = _normalized_hash(text)

        # Daha önce birebir aynı metin hash'i başka bir anahtarla görüldüyse onu kullan
        if text_hash in best_by_hash:
            key = best_by_hash[text_hash]
        else:
            best_by_hash[text_hash] = key

        if key not in best_by_key:
            best_by_key[key] = (doc_id, text)
        else:
            existing_id, existing_text = best_by_key[key]
            if _completeness_score(text) > _completeness_score(existing_text):
                best_by_key[key] = (doc_id, text)

    return list(best_by_key.values())


def dedupe_files(input_dir: Path, output_dir: Path) -> list[Path]:
    """Klasördeki karar_*.txt dosyalarını tekilleştirip hedef klasöre yazar (idempotent)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    records: list[tuple[str, str]] = []
    for path in sorted(input_dir.glob("karar_*.txt")):
        records.append((path.stem, path.read_text(encoding="utf-8")))

    kept = dedupe_decisions(records)
    kept_ids = {doc_id for doc_id, _ in kept}

    # Hedef klasörde önceden kalmış elenen dosya varsa temizle (idempotency)
    if output_dir.resolve() != input_dir.resolve():
        for existing in output_dir.glob("karar_*.txt"):
            if existing.stem not in kept_ids:
                existing.unlink()

    written: list[Path] = []
    for doc_id, text in kept:
        dst = output_dir / f"{doc_id}.txt"
        dst.write_text(text, encoding="utf-8", newline="\n")
        written.append(dst)

    return written