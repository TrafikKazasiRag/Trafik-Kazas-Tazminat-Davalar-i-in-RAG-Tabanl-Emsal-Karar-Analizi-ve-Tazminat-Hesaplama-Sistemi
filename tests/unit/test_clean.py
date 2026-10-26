"""clean.py adımı için genişletilmiş birim ve gerçek veri regresyon testleri."""

import re
from pathlib import Path
import pytest

from trafikrag.ingestion.steps.clean import clean_text, run_clean_dir, _read_file_safe


def test_clean_preserves_all_headings_and_metadata_lines() -> None:
    sample = (
        "Yargıtay 4. Hukuk Dairesi\n"
        "Esas No : 2024/3323\n"
        "Karar No : 2024/5474\n"
        "2023/11230 E. , 2023/13550 K.\n"
        "I. DAVA\n"
        "II. CEVAP\n"
        "IV. GEREKÇE\n"
        "C. Gerekçe\n"
        "V. KARAR\n"
        "VI. KARAR\n"
        "SONUÇ : Davanın kısmen kabulüne,\n"
        "215.180,20 TL\n"
        "14.12.2023 tarihinde oy birliğiyle karar verildi.\n"
    )
    cleaned = clean_text(sample)
    lines = cleaned.splitlines()

    assert "Esas No : 2024/3323" in lines
    assert "Karar No : 2024/5474" in lines
    assert "2023/11230 E. , 2023/13550 K." in lines
    assert "I. DAVA" in lines
    assert "II. CEVAP" in lines
    assert "IV. GEREKÇE" in lines
    assert "C. Gerekçe" in lines
    assert "V. KARAR" in lines
    assert "VI. KARAR" in lines
    assert "SONUÇ : Davanın kısmen kabulüne," in lines
    assert "215.180,20 TL" in lines
    assert "14.12.2023 tarihinde oy birliğiyle karar verildi." in lines


def test_clean_handles_whitespace_and_zerowidth_characters() -> None:
    raw = "215.180,20\u00a0\u200bTL tazminat"
    cleaned = clean_text(raw)
    assert "215.180,20 TL" in cleaned
    assert "\u200b" not in cleaned
    assert "\u00a0" not in cleaned


def test_clean_removes_three_site_noises_and_explicit_page_numbers() -> None:
    minval_noise = (
        "Kararın Özeti; Bu dava trafik kazasına ilişkindir.\n"
        "Ankara Avukat - Minval Hukuk Bürosu\n"
        "Trafik Kazası Tazminatı Hesaplama için TIKLAYINIZ\n"
        "Sayfa 1 / 3\n"
        "Gerçek karar metni burada başlıyor."
    )
    kanun_noise = (
        "Karar Özeti ve Hukuki Bağlam\n"
        "- 3 -\n"
        "Gerçek karar metni ikinci satırda."
    )
    karamercan_noise = (
        "Yargıtay kararı tam metni.\n"
        "Kaynak gösterilmeden kopyalanamaz. Tüm hakları saklıdır © 2024\n"
        "BİLGİ : Bu karar emsal niteliğindedir.\n"
        "B İ L G İ : İçtihat bilgi notudur."
    )

    cleaned_minval = clean_text(minval_noise)
    assert "Kararın Özeti;" not in cleaned_minval
    assert "Ankara Avukat" not in cleaned_minval
    assert "TIKLAYINIZ" not in cleaned_minval
    assert "Sayfa 1 / 3" not in cleaned_minval
    assert "Gerçek karar metni burada başlıyor." in cleaned_minval

    cleaned_kanun = clean_text(kanun_noise)
    assert "Karar Özeti ve Hukuki Bağlam" not in cleaned_kanun
    assert "- 3 -" not in cleaned_kanun
    assert "Gerçek karar metni ikinci satırda." in cleaned_kanun

    cleaned_karamercan = clean_text(karamercan_noise)
    assert "Kaynak gösterilmeden" not in cleaned_karamercan
    assert "BİLGİ :" not in cleaned_karamercan
    assert "B İ L G İ :" not in cleaned_karamercan
    assert "Yargıtay kararı tam metni." in cleaned_karamercan


def test_clean_removes_generic_domain_and_bracketed_page_no() -> None:
    """Yeni eklenen jenerik domain regex'lerinin ve köşeli sayfa kalıplarının temizliğini test eder."""
    raw = (
        "Kaynak: www.emsalicthatlar.net\n"
        "[ Sayfa 1 ]\n"
        "Bursa Avukat - Örnek Bürosu\n"
        "I. DAVA\n"
        "Tazminat talebi."
    )
    cleaned = clean_text(raw)
    assert "emsalicthatlar.net" not in cleaned
    assert "[ Sayfa 1 ]" not in cleaned
    assert "Bursa Avukat" not in cleaned
    assert "I. DAVA" in cleaned
    assert "Tazminat talebi." in cleaned


def test_clean_does_not_delete_legitimate_decision_sentences_and_ratios() -> None:
    legitimate_lines = [
        "Davalı Minval Hukuk Sigorta A.Ş. vekili temyiz etti.",
        "Davacı vekili Ankara Avukat Ornek Kisi dilekçe verdi.",
        "Bilgi : bilirkişi raporu dosyaya sunulmuştur.",
        "Davacının tüm hakları saklıdır, fazlaya ilişkin talep hakkı saklıdır.",
        "15",
        "1/2",
    ]
    sample = "\n".join(legitimate_lines)
    cleaned = clean_text(sample)
    cleaned_lines = cleaned.splitlines()

    for expected_line in legitimate_lines:
        assert expected_line in cleaned_lines


def test_clean_is_idempotent() -> None:
    sample = "Yargıtay 4. Hukuk Dairesi\nEsas No: 2023/1\nI. DAVA\nMetin."
    once = clean_text(sample)
    twice = clean_text(once)
    assert once == twice


def test_clean_does_not_modify_raw_files_and_writes_to_interim(tmp_path: Path) -> None:
    raw_dir = tmp_path / "data" / "raw"
    interim_dir = tmp_path / "data" / "interim"
    raw_dir.mkdir(parents=True)

    original_content = (
        "Yargıtay 4. Hukuk Dairesi\n"
        "Esas No: 2023/1\n"
        "I. DAVA\n"
        "Trafik Kazası Tazminatı Hesaplama için TIKLAYINIZ\n"
        "Metin."
    )
    src_file = raw_dir / "karar_01.txt"
    src_file.write_text(original_content, encoding="utf-8")

    run_clean_dir(raw_dir, interim_dir)

    assert src_file.read_text(encoding="utf-8") == original_content
    dst_file = interim_dir / "karar_01.txt"
    assert dst_file.exists()
    assert "TIKLAYINIZ" not in dst_file.read_text(encoding="utf-8")


def test_read_file_safe_handles_non_utf8_encodings(tmp_path: Path) -> None:
    """YENİ TEST: cp1254 (Türkçe Windows) formatında kaydedilmiş dosyaların patlamadan okunduğunu doğrular."""
    cp1254_file = tmp_path / "cp1254_karar.txt"
    turkish_text = "Yargıtay Kararı: Şüpheli durumlar çözüldü. (Türkçe karakter testi: ğüşiöç)"
    cp1254_file.write_bytes(turkish_text.encode("cp1254"))

    read_content = _read_file_safe(cp1254_file)
    assert "Şüpheli durumlar" in read_content
    assert "ğüşiöç" in read_content


def test_run_clean_dir_processes_any_txt_file_name(tmp_path: Path) -> None:
    """YENİ TEST: Sadece karar_*.txt değil, her türlü .txt uzantılı dosyayı temizlediğini doğrular."""
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()

    custom_named_file = input_dir / "2024_3323_esas.txt"
    custom_named_file.write_text("Yargıtay 4. HD\nAnkara Avukat\nGerçek Metin", encoding="utf-8")

    run_clean_dir(input_dir, output_dir)

    out_file = output_dir / "2024_3323_esas.txt"
    assert out_file.exists()
    assert "Ankara Avukat" not in out_file.read_text(encoding="utf-8")
    assert "Gerçek Metin" in out_file.read_text(encoding="utf-8")


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def test_real_decisions_regression_with_injected_noise() -> None:
    """data/raw dizinindeki tüm gerçek kararlara gürültü enjekte edip temizliği doğrular."""
    fake_header_noise = (
        "Anasayfa > Yargıtay Kararları > 4. Hukuk Dairesi\n"
        "Kararın Özeti; Yaralanmalı trafik kazası maddi tazminat davasıdır.\n"
        "Karar Özeti ve Hukuki Bağlam\n"
        "Ankara Avukat - Minval Hukuk Bürosu\n"
        "Trafik Kazası Tazminatı Hesaplama için TIKLAYINIZ\n"
        "Sayfa 1 / 4\n"
    )
    fake_footer_noise = (
        "\n- 4 -\n"
        "Bu karar Karamercan Hukuk tarafından derlenmiştir.\n"
        "Kaynak gösterilmeden kopyalanamaz.\n"
        "Tüm hakları saklıdır © 2024\n"
        "BİLGİ : İçtihat bilgi notudur.\n"
    )

    raw_dir = Path("data/raw")
    raw_files = sorted(raw_dir.glob("karar_*.txt"))

    if not raw_files:
        pytest.skip("data/raw dizininde test edilecek gerçek karar dosyası bulunamadı.")

    for src in raw_files:
        original_text = None
        for enc in ("utf-8", "cp1254", "latin-1"):
            try:
                original_text = src.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue

        if not original_text:
            continue

        noisy_text = f"{fake_header_noise}\n{original_text}\n{fake_footer_noise}"

    if not files:
        pytest.skip("Projede test edilecek .txt karar dosyası bulunamadı.")

    for src in files:
        text = None
        for enc in ("utf-8", "cp1254", "latin-1"):
            try:
                text = src.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue

        assert orig_parsed.court == clean_parsed.court
        assert orig_parsed.esas_no == clean_parsed.esas_no
        assert orig_parsed.karar_no == clean_parsed.karar_no
        assert orig_parsed.date == clean_parsed.date
        assert [s.kind for s in orig_parsed.sections] == [s.kind for s in clean_parsed.sections]

        assert _normalize_ws(cleaned_noisy) == _normalize_ws(original_text)
        assert cleaned_noisy == cleaned_original
