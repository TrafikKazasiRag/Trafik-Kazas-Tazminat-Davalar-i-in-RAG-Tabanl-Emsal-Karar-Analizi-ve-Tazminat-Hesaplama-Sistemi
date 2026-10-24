"""anonymize.py adımı için birim testler (tamamen kurgusal/uydurma test verileri)."""
from pathlib import Path
from trafikrag.ingestion.steps.anonymize import anonymize_file, anonymize_text


def test_anonymize_masks_tckn_plate_phone_iban_email_address() -> None:
    sample = (
        "Davacıya ait 12345678901 T.C. kimlik numaralı kayıt incelendi.\n"
        "Kazaya karışan 06 ABC 123 plakalı araç ile 34 XY 9876 plakalı aracın çarpışması sonucunda,\n"
        "İletişim: 0532 123 45 67 ve ornek.kisi@example.com üzerinden bildirim yapılmıştır.\n"
        "Ödeme TR12 0006 1005 1978 6457 8413 26 numaralı IBAN hesabına yatırılmıştır.\n"
        "İkametgah: Cumhuriyet Mah. Atatürk Bulvarı Çiçek Sok. No: 12/4 Çankaya/Ankara adresindedir.\n"
    )
    masked = anonymize_text(sample)

    assert "12345678901" not in masked
    assert "[TCKN]" in masked

    assert "06 ABC 123" not in masked
    assert "34 XY 9876" not in masked
    assert "[PLAKA]" in masked

    assert "0532 123 45 67" not in masked
    assert "[TELEFON]" in masked

    assert "ornek.kisi@example.com" not in masked
    assert "[EPOSTA]" in masked

    assert "TR12 0006" not in masked
    assert "[IBAN]" in masked

    assert "Çiçek Sok. No: 12/4" not in masked
    assert "[ADRES]" in masked


def test_anonymize_masks_person_names_and_abbreviations() -> None:
    # Kurgusal isimler: bağlam içi, isim listesi tabanlı ve kısaltmalı ("Gamze V.") örnekler
    sample = (
        "Davacı Ahmet Yılmaz vekili Av. Mehmet Kaya tarafından açılan davada;\n"
        "Davalı sürücü Mustafa Demir ile sigortalı Ayşe Çelik kusurlu bulunmuştur.\n"
        "Yargıtay ilamında geçen Gamze V. ve H. K. isimli şahısların ifadeleri alınmıştır.\n"
    )
    masked = anonymize_text(sample)

    assert "Ahmet Yılmaz" not in masked
    assert "Mehmet Kaya" not in masked
    assert "Mustafa Demir" not in masked
    assert "Ayşe Çelik" not in masked
    assert "Gamze V." not in masked
    assert "[KİŞİ]" in masked


def test_anonymize_preserves_numbers_amounts_dates_and_courts(tmp_path: Path) -> None:
    sample = (
        "Yargıtay 4. Hukuk Dairesi\n"
        "Esas No: 2023/11230\n"
        "Karar No: 2023/13550\n"
        "I. DAVA\n"
        "Ankara 3. Asliye Ticaret Mahkemesi ve Adli Tıp Kurumu raporuna göre %75 kusur oranı ile\n"
        "215.180,20 TL sürekli iş göremezlik tazminatının 14.12.2023 tarihinden itibaren\n"
        "işleyecek yasal faiziyle davalıdan tahsiline karar verilmiştir.\n"
        "IV. GEREKÇE\n"
        "6098 sayılı Türk Borçlar Kanunu ve 2918 sayılı Karayolları Trafik Kanunu uyarınca...\n"
        "V. KARAR\n"
        "SONUÇ : 30.05.2024 tarihinde oy birliğiyle karar verildi.\n"
    )
    masked = anonymize_text(sample)

    # Künye, mahkeme/kurum adları, kanun numaraları, tutarlar ve tarihler bozulmamalı
    assert "Yargıtay 4. Hukuk Dairesi" in masked
    assert "Esas No: 2023/11230" in masked
    assert "Karar No: 2023/13550" in masked
    assert "Ankara 3. Asliye Ticaret Mahkemesi" in masked
    assert "Adli Tıp Kurumu" in masked
    assert "%75" in masked
    assert "215.180,20 TL" in masked
    assert "14.12.2023" in masked
    assert "30.05.2024" in masked
    assert "6098 sayılı" in masked
    assert "2918 sayılı" in masked
    assert "I. DAVA" in masked
    assert "IV. GEREKÇE" in masked
    assert "V. KARAR" in masked

    # Idempotency (iki kez çalıştırıldığında aynı sonuç) ve dosya testi
    twice = anonymize_text(masked)
    assert masked == twice

    src = tmp_path / "karar_01.txt"
    dst = tmp_path / "out" / "karar_01.txt"
    src.write_text(sample, encoding="utf-8", newline="\n")
    anonymize_file(src, dst)
    assert dst.read_text(encoding="utf-8") == masked