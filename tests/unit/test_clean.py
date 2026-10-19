"""clean.py adımı için birim testler (gerçek kişi adı içermez, kurgusal/anonim örnekler)."""
from pathlib import Path
from trafikrag.ingestion.steps.clean import clean_file, clean_text


def test_clean_removes_site_noise_and_ads() -> None:
    raw = (
        "Anasayfa > Yargıtay Kararları > 4. Hukuk Dairesi\n"
        "Trafik Kazası Tazminatı Hesaplama için TIKLAYINIZ\n"
        "Ankara Avukat - Minval Hukuk Bürosu\n"
        "T.C.\n"
        "YARGITAY\n"
        "4. Hukuk Dairesi\n"
        "Esas No: 2023/11230\n"
        "Karar No: 2023/13550\n"
        "Bu karar Karamercan Hukuk tarafından derlenmiştir. Kaynak gösterilmeden kopyalanamaz.\n"
        "Tüm hakları saklıdır © 2024\n"
    )
    cleaned = clean_text(raw)

    assert "TIKLAYINIZ" not in cleaned
    assert "Ankara Avukat" not in cleaned
    assert "Minval Hukuk" not in cleaned
    assert "Karamercan Hukuk" not in cleaned
    assert "Kaynak gösterilmeden" not in cleaned
    assert "Tüm hakları saklıdır" not in cleaned
    assert "Anasayfa >" not in cleaned
    # Künye bilgileri korunmalı
    assert "4. Hukuk Dairesi" in cleaned
    assert "Esas No: 2023/11230" in cleaned
    assert "Karar No: 2023/13550" in cleaned


def test_clean_preserves_section_headings_and_metadata() -> None:
    raw = (
        "   4. Hukuk Dairesi   \n\n\n\n"
        "Esas No : 2023/11230\n"
        "Karar No : 2023/13550\n\n"
        "   I. DAVA   \n"
        "Davacı vekili dava dilekçesinde; yaralanmalı trafik kazası nedeniyle maddi tazminat talep etmiştir.\n\n\n"
        "   IV. GEREKÇE   \n"
        "Bilirkişi raporunda kusur oranı %75 olarak belirlenmiştir.\n\n"
        "   V. KARAR   \n"
        "SONUÇ : Yukarıda açıklanan nedenlerle kararın BOZULMASINA, 14.12.2023 tarihinde oy birliğiyle karar verildi.\n"
    )
    cleaned = clean_text(raw)

    # parse_decision.py'nin bağlı olduğu başlıklar satır başında ve bozulmadan durmalı
    lines = cleaned.splitlines()
    assert "I. DAVA" in lines
    assert "IV. GEREKÇE" in lines
    assert "V. KARAR" in lines
    assert any(line.startswith("SONUÇ :") for line in lines)
    assert "14.12.2023 tarihinde" in cleaned
    # Üç veya daha fazla ardışık boş satır tek boş satıra (en fazla \n\n) indirilmeli
    assert "\n\n\n" not in cleaned


def test_clean_normalizes_unicode_and_is_idempotent(tmp_path: Path) -> None:
    # NFD biçimindeki ayrık karakter (örn. i + birleşen nokta) NFC'ye dönmeli ve adım idempotent olmalı
    raw = (
        "4. Hukuk Dairesi\r\n"
        "Esas No: 2023/100\r\n"
        "I. DAVA\r\n"
        "Davacı\u00a0vekili\t\t215.180,20 TL\u200b tazminat istemiştir.\r\n"
        "IV. GEREKÇE\r\n"
        "Gerekçe metni.\r\n"
        "V. KARAR\r\n"
        "30.05.2024 tarihinde karar verildi.\r\n"
    )
    once = clean_text(raw)
    twice = clean_text(once)

    # Idempotency: iki kez çalıştırılınca birebir aynı çıktıyı vermeli
    assert once == twice
    # Tutarlar bozulmamalı, görünmez boşluklar (\u200b, \u00a0) ve fazla tab'lar temizlenmeli
    assert "215.180,20 TL" in once
    assert "\u200b" not in once
    assert "\u00a0" not in once
    assert "\r" not in once

    # Dosya bazlı çalışma testi
    src_file = tmp_path / "karar_01.txt"
    dst_file = tmp_path / "out" / "karar_01.txt"
    src_file.write_text(raw, encoding="utf-8", newline="")

    out_path = clean_file(src_file, dst_file)
    assert out_path == dst_file
    assert dst_file.read_text(encoding="utf-8") == once