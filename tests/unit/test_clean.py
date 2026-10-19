"""clean.py adımı için kapsamlı birim ve regresyon testleri (Madde 1-17)."""
from pathlib import Path
import pytest

from trafikrag.ingestion.steps.clean import clean_file, clean_text, run_clean_dir
from trafikrag.ingestion.steps.parse_decision import parse_decision


def test_clean_preserves_all_headings_and_metadata_lines() -> None:
    sample = (
        "Yargıtay 4. Hukuk Dairesi\n"
        "Esas No : 2024/3323\n"
        "Karar No : 2024/5474\n"
        "2023/11230 E. , 2023/13550 K.\n"
        "I. DAVA\n"
        "IV. GEREKÇE\n"
        "V. KARAR\n"
        "215.180,20 TL\n"
        "14.12.2023 tarihinde oy birliğiyle karar verildi.\n"
    )
    cleaned = clean_text(sample)
    lines = cleaned.splitlines()

    assert "Esas No : 2024/3323" in lines
    assert "Karar No : 2024/5474" in lines
    assert "I. DAVA" in lines
    assert "IV. GEREKÇE" in lines
    assert "V. KARAR" in lines
    assert "215.180,20 TL" in lines
    assert "14.12.2023 tarihinde oy birliğiyle karar verildi." in lines


def test_clean_handles_whitespace_and_zerowidth_characters() -> None:
    # Madde 8: \u00a0 normal boşluğa çevrilmeli, \u200b silinmeli
    raw = "215.180,20\u00a0\u200bTL tazminat"
    cleaned = clean_text(raw)
    assert "215.180,20 TL" in cleaned
    assert "\u200b" not in cleaned
    assert "\u00a0" not in cleaned


def test_clean_removes_three_site_noises() -> None:
    # Madde 9: Minval, Kanunyolu ve Karamercan gürültüleri testleri (uydurma örnekler)
    minval_noise = (
        "Kararın Özeti; Bu dava trafik kazasına ilişkindir.\n"
        "Ankara Avukat bürosu açıklaması.\n"
        "Trafik Kazası Tazminatı Hesaplama için TIKLAYINIZ\n"
        "Gerçek karar metni burada başlıyor."
    )
    kanun_noise = (
        "Karar Özeti ve Hukuki Bağlam\n"
        "Editoryal açıklamalar ve menü blokları.\n"
        "Gerçek karar metni ikinci satırda."
    )
    karamercan_noise = (
        "Yargıtay kararı tam metni.\n"
        "Kaynak gösterilmeden kopyalanamaz. Tüm hakları saklıdır.\n"
        "BİLGİ : Bu karar emsal niteliğindedir."
    )

    assert "Kararın Özeti;" not in clean_text(minval_noise)
    assert "Ankara Avukat" not in clean_text(minval_noise)
    assert "TIKLAYINIZ" not in clean_text(minval_noise)
    assert "Gerçek karar metni burada başlıyor." in clean_text(minval_noise)

    assert "Karar Özeti ve Hukuki Bağlam" not in clean_text(kanun_noise)
    assert "Gerçek karar metni ikinci satırda." in clean_text(kanun_noise)

    assert "Kaynak gösterilmeden" not in clean_text(karamercan_noise)
    assert "BİLGİ :" not in clean_text(karamercan_noise)
    assert "Yargıtay kararı tam metni." in clean_text(karamercan_noise)


def test_clean_is_idempotent() -> None:
    # Madde 10 & 11: clean_text(clean_text(x)) == clean_text(x)
    sample = "Yargıtay 4. Hukuk Dairesi\nEsas No: 2023/1\nI. DAVA\nMetin."
    once = clean_text(sample)
    twice = clean_text(once)
    assert once == twice


def test_clean_does_not_modify_raw_files_and_writes_to_interim(tmp_path: Path) -> None:
    # Madde 14 & 15: run_clean_dir raw'dan okur, interim'e yazar, raw değişmez
    raw_dir = tmp_path / "data" / "raw"
    interim_dir = tmp_path / "data" / "interim"
    raw_dir.mkdir(parents=True)

    original_content = "Yargıtay 4. Hukuk Dairesi\nEsas No: 2023/1\nI. DAVA\nTıklayınız\nMetin."
    src_file = raw_dir / "karar_01.txt"
    src_file.write_text(original_content, encoding="utf-8")

    run_clean_dir(raw_dir, interim_dir)

    # Ham dosya içeriği tamamen aynı kalmalı (Madde 14)
    assert src_file.read_text(encoding="utf-8") == original_content
    # Interim dosyası temizlenmiş olmalı
    dst_file = interim_dir / "karar_01.txt"
    assert dst_file.exists()
    assert "Tıklayınız" not in dst_file.read_text(encoding="utf-8")


@pytest.mark.skipif(
    not (Path("data/raw/karar_01.txt").exists() or Path("data/raw/karar_02.txt").exists() or Path("data/raw/karar_03.txt").exists()),
    reason="data/raw içinde gerçek karar dosyaları bulunamadı (yerelde çalışır)",
)
def test_real_decisions_regression() -> None:
    # Madde 12 & 13: Gerçek kararlarla regresyon testi (dosya yoksa skip edilir)
    raw_dir = Path("data/raw")
    for src in raw_dir.glob("karar_*.txt"):
        raw_text = src.read_text(encoding="utf-8")
        cleaned_text = clean_text(raw_text)

        raw_parsed = parse_decision(raw_text, src.stem)
        clean_parsed = parse_decision(cleaned_text, src.stem)

        assert raw_parsed.court == clean_parsed.court
        assert raw_parsed.esas_no == clean_parsed.esas_no
        assert raw_parsed.karar_no == clean_parsed.karar_no
        assert raw_parsed.date == clean_parsed.date
        assert len(raw_parsed.sections) == len(clean_parsed.sections)
        for r_sec, c_sec in zip(raw_parsed.sections, clean_parsed.sections):
            assert r_sec.kind == c_sec.kind