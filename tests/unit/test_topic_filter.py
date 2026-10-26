"""topic_filter.py adımı için güncellenmiş birim testler."""
from pathlib import Path
from trafikrag.ingestion.steps.topic_filter import (
    detect_outcome,
    evaluate_decision,
    run_topic_filter,
)


def test_topic_filter_rejects_criminal_kasko_tutanak_and_procedural() -> None:
    # 1. Ceza dairesi kararı -> elenmeli
    ceza_text = (
        "Yargıtay 12. Ceza Dairesi\n"
        "Esas No: 2023/100\nKarar No: 2023/200\n"
        "Taksirle yaralama suçundan sanığın mahkumiyetine dair hükmün ONANMASINA, 10.05.2023 tarihinde karar verildi."
    )
    res_ceza = evaluate_decision("eski_01", ceza_text)
    assert res_ceza.kabul_edildi is False
    assert "mahkeme" in res_ceza.sebep or "ceza" in res_ceza.sebep

    # 2. Kaza tespit tutanağı iptali -> elenmeli
    tutanak_text = (
        "Yargıtay 4. Hukuk Dairesi\n"
        "Esas No: 2022/500\nKarar No: 2022/600\n"
        "I. DAVA\nDavacı, kaza tespit tutanağının iptali isteminde bulunmuştur.\n"
        "V. KARAR\nSONUÇ : Tutanağın iptali talebinin reddine, 12.06.2022 tarihinde karar verildi."
    )
    res_tutanak = evaluate_decision("eski_02", tutanak_text)
    assert res_tutanak.kabul_edildi is False
    assert "tutanak" in res_tutanak.sebep

    # 3. Sadece kasko / araç hasarı / değer kaybı -> elenmeli
    kasko_text = (
        "Yargıtay 4. Hukuk Dairesi\n"
        "Esas No: 2023/700\nKarar No: 2023/800\n"
        "I. DAVA\nKasko sigorta poliçesinden kaynaklanan araç hasarı ve değer kaybı bedelinin tahsili istemidir.\n"
        "IV. GEREKÇE\nBilirkişi raporunda %50 kusur oranı belirlenmiştir.\n"
        "V. KARAR\nSONUÇ : Hükmün ONANMASINA, 15.09.2023 tarihinde karar verildi."
    )
    res_kasko = evaluate_decision("eski_03", kasko_text)
    assert res_kasko.kabul_edildi is False
    assert "arac_hasari" in res_kasko.sebep or "kasko" in res_kasko.sebep


def test_topic_filter_accepts_bam_and_other_courts() -> None:
    # BAM / Bölge Adliye Mahkemesi kararı -> Artık elenmemeli (1. Madde Düzeltmesi)
    bam_text = (
        "Ankara Bölge Adliye Mahkemesi 26. Hukuk Dairesi\n"
        "Esas No: 2023/101\nKarar No: 2023/202\n"
        "I. DAVA\n"
        "Yaralanmalı trafik kazası nedeniyle geçici iş göremezlik ve maluliyet tazminatı talebidir.\n"
        "IV. GEREKÇE\nBilirkişi raporunda %100 kusur oranı tespit edilmiştir.\n"
        "V. KARAR\nSONUÇ : Istinaf başvurusunun esastan reddine karar verildi."
    )
    res_bam = evaluate_decision("bam_01", bam_text)
    assert res_bam.kabul_edildi is True
    assert res_bam.sonuc == "istinaf_reddi"


def test_detect_outcome_dictionary_alignment() -> None:
    # ExtractedFacts.outcome sözlük hizalaması (3. Madde Düzeltmesi)
    assert detect_outcome("istinaf başvurusunun esastan reddine karar verildi") == "istinaf_reddi"
    assert detect_outcome("ilk derece mahkemesi kararının kaldırılmasına ve yeniden hüküm kurulmasına") == "kaldirma"
    assert detect_outcome("hükmün bozulmasına") == "bozma"


def test_topic_filter_handles_fatal_support_claims_and_preserves_data(tmp_path: Path) -> None:
    # Ölümlü kaza (destekten yoksun kalma) -> kabul_edildi=False ama silinmez, rejected_dir'e kopyalanır (2. Madde Düzeltmesi)
    destek_text = (
        "Yargıtay 4. Hukuk Dairesi\n"
        "Esas No: 2023/111\nKarar No: 2023/222\n"
        "I. DAVA\nDavacılar, trafik kazasında vefat eden yakınları nedeniyle destekten yoksun kalma tazminatı istemiştir.\n"
        "IV. GEREKÇE\nBilirkişi raporunda %75 kusur oranı hesaplanmıştır.\n"
        "V. KARAR\nSONUÇ : Hükmün BOZULMASINA, 20.10.2023 tarihinde karar verildi."
    )
    res_destek = evaluate_decision("karar_01", destek_text)
    assert res_destek.kabul_edildi is False
    assert "destek" in res_destek.konu_etiketi

    # Veri kaybı testi: rejected_dir alanına kopyalanması
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    rej_dir = tmp_path / "rejected"
    log_csv = tmp_path / "selection_log.csv"
    in_dir.mkdir()

    (in_dir / "karar_01.txt").write_text(destek_text, encoding="utf-8", newline="\n")

    accepted_paths = run_topic_filter(in_dir, out_dir, log_path=log_csv, rejected_dir=rej_dir)
    assert len(accepted_paths) == 0
    assert (rej_dir / "karar_01.txt").exists()  # Veri silinmedi, ayrıştırıldı!


def test_topic_filter_accepts_valid_injury_decision_and_writes_log(tmp_path: Path) -> None:
    valid_text = (
        "Yargıtay 4. Hukuk Dairesi\n"
        "Esas No: 2023/11230\nKarar No: 2023/13550\n"
        "I. DAVA\n"
        "Davacı vekili; yaralanmalı trafik kazası sonucunda müvekkilinin malul kaldığını belirterek "
        "sürekli iş göremezlik, geçici iş göremezlik ve bakıcı gideri maddi tazminatlarının tahsilini istemiştir.\n"
        "IV. GEREKÇE\n"
        "Adli Tıp Kurumu ve bilirkişi raporuna göre davalı sürücü %75 oranında kusurlu olup maluliyet oranı %18'dir.\n"
        "V. KARAR\n"
        "SONUÇ : Davanın kısmen kabulüne dair kararın BOZULMASINA, 14.12.2023 tarihinde oy birliğiyle karar verildi.\n"
    )
    res_valid = evaluate_decision("karar_03", valid_text)
    assert res_valid.kabul_edildi is True
    assert "iscilik" in res_valid.konu_etiketi
    assert "bakici" in res_valid.konu_etiketi
    assert "kusur" in res_valid.konu_etiketi
    assert res_valid.sonuc == "bozma"

    # Klasör ve CSV log testi
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    log_csv = tmp_path / "selection_log.csv"
    in_dir.mkdir()

    (in_dir / "karar_03.txt").write_text(valid_text, encoding="utf-8", newline="\n")

    accepted_paths = run_topic_filter(in_dir, out_dir, log_csv)
    assert len(accepted_paths) == 1
    assert log_csv.exists()
    csv_content = log_csv.read_text(encoding="utf-8")
    assert "karar_03,True," in csv_content