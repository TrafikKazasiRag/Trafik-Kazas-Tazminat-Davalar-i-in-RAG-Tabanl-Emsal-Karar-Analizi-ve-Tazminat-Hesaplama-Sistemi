"""dedupe.py adımı için birim testler."""
from pathlib import Path
from trafikrag.ingestion.steps.dedupe import dedupe_decisions, dedupe_files


def test_dedupe_keeps_most_complete_when_same_esas_and_karar_no() -> None:
    # Aynı kararın (2023/11230 E., 2023/13550 K.) iki farklı biçimi: biri kısa/eksik, diğeri tam metin
    short_version = (
        "4. Hukuk Dairesi\n"
        "Esas No: 2023/11230\n"
        "Karar No: 2023/13550\n"
        "I. DAVA\n"
        "Özet karar metni.\n"
    )
    complete_version = (
        "Yargıtay 4. Hukuk Dairesi\n"
        "2023/11230 E. , 2023/13550 K.\n"
        "I. DAVA\n"
        "Davacı vekili yaralanmalı trafik kazası nedeniyle maddi tazminat talep etmiştir.\n"
        "IV. GEREKÇE\n"
        "Bilirkişi raporuna göre davalı sürücü %75 kusurludur.\n"
        "V. KARAR\n"
        "SONUÇ : Hüküm onanmıştır. 14.12.2023 tarihinde oy birliğiyle karar verildi.\n"
    )
    distinct_decision = (
        "4. Hukuk Dairesi\n"
        "Esas No: 2024/100\n"
        "Karar No: 2024/200\n"
        "I. DAVA\n"
        "Farklı bir trafik kazası dosyası.\n"
    )

    records = [
        ("karar_01", short_version),
        ("karar_02", complete_version),
        ("karar_03", distinct_decision),
    ]

    kept = dedupe_decisions(records)

    # 3 kayıttan 2'si kalmalı; mükerrer olanlardan en eksiksiz olan (karar_02) tutulmalı
    assert len(kept) == 2
    kept_ids = [doc_id for doc_id, _ in kept]
    assert "karar_02" in kept_ids
    assert "karar_03" in kept_ids
    assert "karar_01" not in kept_ids

    # Idempotency: tekrar çalıştırıldığında aynı listeyi dönmeli
    assert dedupe_decisions(kept) == kept


def test_dedupe_by_normalized_text_hash_when_numbers_missing(tmp_path: Path) -> None:
    # Künye numarası okunamasa bile metin içeriği (boşluk/noktalama farkı dışında) aynıysa tek kayıt kalmalı
    text_a = "I. DAVA\nDavacı yaralanmalı kaza sonucu tazminat istemiştir.\nSONUÇ : Kabul."
    text_b = "I. DAVA\n\n  Davacı   yaralanmalı kaza sonucu tazminat istemiştir. \nSONUÇ : Kabul."

    src_dir = tmp_path / "in"
    dst_dir = tmp_path / "out"
    src_dir.mkdir()

    (src_dir / "karar_01.txt").write_text(text_a, encoding="utf-8", newline="\n")
    (src_dir / "karar_02.txt").write_text(text_b, encoding="utf-8", newline="\n")

    written = dedupe_files(src_dir, dst_dir)
    assert len(written) == 1