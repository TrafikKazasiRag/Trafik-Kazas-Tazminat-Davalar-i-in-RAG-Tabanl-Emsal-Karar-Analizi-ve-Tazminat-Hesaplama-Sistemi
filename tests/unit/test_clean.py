"""clean.py adımı için kapsamlı birim ve regresyon testleri."""
import re
from pathlib import Path
import pytest

from trafikrag.ingestion.steps.clean import clean_text, run_clean_dir
from trafikrag.ingestion.steps.parse_decision import parse_decision


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
        "B İ L G İ : İçtihat notu."
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


def test_clean_does_not_delete_legitimate_decision_sentences_and_ratios() -> None:
    # Buğra'nın belirttiği 5 kritik false-positive senaryosu (uydurma isimlerle)
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


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@pytest.mark.skipif(
    not (
        Path("data/raw/karar_01.txt").exists()
        or Path("data/raw/karar_02.txt").exists()
        or Path("data/raw/karar_03.txt").exists()
    ),
    reason="data/raw içinde gerçek karar dosyaları bulunamadı (yerelde çalışır)",
)
def test_real_decisions_regression_with_injected_noise() -> None:
    # Madde 4: Gerçek kararların başına ve sonuna sahte site gürültüsü ekleyip temizledikten sonra
    # hem parse_decision çıktısı hem de metin (boşluk farkı hariç) orijinalle birebir aynı olmalı.
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
    for src in sorted(raw_dir.glob("karar_*.txt")):
        original_text = src.read_text(encoding="utf-8")
        noisy_text = f"{fake_header_noise}\n{original_text}\n{fake_footer_noise}"

        cleaned_noisy = clean_text(noisy_text)
        cleaned_original = clean_text(original_text)

        orig_parsed = parse_decision(original_text, src.stem)
        clean_parsed = parse_decision(cleaned_noisy, src.stem)

        # 1. parse_decision sonuçları (daire, esas, karar, tarih, bölüm türleri) aynı olmalı
        assert orig_parsed.court == clean_parsed.court
        assert orig_parsed.esas_no == clean_parsed.esas_no
        assert orig_parsed.karar_no == clean_parsed.karar_no
        assert orig_parsed.date == clean_parsed.date
        assert [s.kind for s in orig_parsed.sections] == [s.kind for s in clean_parsed.sections]

        # 2. Temizlenmiş gürültülü metin, gürültüsüz orijinalle (boşluk farkı hariç) birebir aynı olmalı
        assert _normalize_ws(cleaned_noisy) == _normalize_ws(original_text)
        assert cleaned_noisy == cleaned_original