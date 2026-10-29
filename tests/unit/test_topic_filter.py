"""topic_filter.py adımı için güncellenmiş birim testler."""
from pathlib import Path
from trafikrag.ingestion.steps.topic_filter import (
    detect_outcome,
    evaluate_decision,
    run_topic_filter,
)


def test_topic_filter_rejects_criminal_and_danistay_via_court_metadata() -> None:
    # 1. Ceza dairesi kararı
    ceza_text = (
        "Yargıtay 12. Ceza Dairesi\n"
        "Esas No: 2023/100\nKarar No: 2023/200\n"
        "Taksirle yaralama suçundan sanığın mahkumiyetine dair hükmün ONANMASINA, 10.05.2023 tarihinde karar verildi."
    )
    res_ceza = evaluate_decision("eski_01", ceza_text)
    assert res_ceza.kabul_edildi is False
    assert res_ceza.sebep == "mahkeme_uyumsuz_ceza_veya_danistay"

    # 2. Danıştay kararı
    danistay_text = (
        "Danıştay 8. Dairesi\n"
        "Esas No: 2022/100\nKarar No: 2022/200\n"
        "İdari işlemin iptaline dair kararın onanmasına karar verildi."
    )
    res_danistay = evaluate_decision("eski_danistay", danistay_text)
    assert res_danistay.kabul_edildi is False
    assert res_danistay.sebep == "mahkeme_uyumsuz_ceza_veya_danistay"


def test_topic_filter_rejects_kasko_tutanak_and_procedural() -> None:
    # 1. Kaza tespit tutanağı iptali -> elenmeli
    tutanak_text = (
        "Yargıtay 4. Hukuk Dairesi\n"
        "Esas No: 2022/500\nKarar No: 2022/600\n"
        "I. DAVA\nDavacı, kaza tespit tutanağının iptali isteminde bulunmuştur.\n"
        "V. KARAR\nSONUÇ : Tutanağın iptali talebinin reddine, 12.06.2022 tarihinde karar verildi."
    )
    res_tutanak = evaluate_decision("eski_02", tutanak_text)
    assert res_tutanak.kabul_edildi is False
    assert "tutanak" in res_tutanak.sebep

    # 2. Sadece kasko / araç hasarı / değer kaybı -> elenmeli
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
    # BAM / Bölge Adliye Mahkemesi kararı
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
    assert detect_outcome("istinaf başvurusunun esastan reddine karar verildi") == "istinaf_reddi"
    assert detect_outcome("ilk derece mahkemesi kararının kaldırılmasına ve yeniden hüküm kurulmasına") == "kaldirma"
    assert detect_outcome("hükmün bozulmasına") == "bozma"
    assert detect_outcome("onanmasına") == "istinaf_reddi"


def test_detect_outcome_cok_maddeli_hukum() -> None:
    text = """
    HÜKÜM : Gerekçesi yukarıda açıklandığı üzere;
    1- Davanın KISMEN KABULÜ ile 45.000 TL maddi tazminatın davalıdan tahsiline,
    2- Fazlaya ilişkin talebin reddine,
    3- Harç ve yargılama giderlerinin davalıdan tahsiline karar verildi.
    """ + (" " * 2000)
    
    assert detect_outcome(text) == "kismen_kabul"


def test_detect_outcome_bam_esastan_red_araya_madde_girmis() -> None:
    text = """
    GEREĞİ DÜŞÜNÜLDÜ:
    Davacı vekilinin istinaf başvurusunun HMK'nın 353/1-b/1. maddesi uyarınca ESASTAN REDDİNE,
    dosya üzerinden yapılan inceleme sonucunda oy birliğiyle karar verildi.
    """
    assert detect_outcome(text) == "istinaf_reddi"


def test_evaluate_decision_belirsiz_sonuclar_elenmemeli() -> None:
    text = "T.C. Ankara Asliye Hukuk Mahkemesi.\n" + ("Metin boşluğu " * 100) + "Yaralanmalı trafik kazası kaynaklı geçici iş göremezlik tazminatı. Kusur oranı %100. Hüküm kısmı standart dışı."
    res = evaluate_decision("karar_belirsiz", text)
    
    assert res.kabul_edildi is True
    assert res.sonuc == "belirsiz"
    assert "sonuc_belirsiz" in res.konu_etiketi


def test_evaluate_decision_ceza_kontrolu_sadece_kunyede() -> None:
    # Emsal atfı olarak geçen 'ceza dairesi' ifadesi 'court' künyesinde yer almadığı için kararı eletmemeli
    text = "T.C.\nANKARA 3. ASLİYE HUKUK MAHKEMESİ\n" + ("Ara Metin " * 300) + "Yargıtay 12. Ceza Dairesi kararına atıf yapılmıştır. Yaralanmalı maluliyet ve kusur %50 tespit edilmiştir."
    res = evaluate_decision("test_emsal_ceza", text)
    
    assert res.kabul_edildi is True
    assert res.sebep == "kabul_yaralanmali_maddi_tazminat"


def test_topic_filter_handles_fatal_support_claims_and_preserves_data(tmp_path: Path) -> None:
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
    assert res_destek.sebep == "kapsam_disi_olumlu_destek_ayri_sakla"

    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    rej_dir = tmp_path / "rejected"
    log_csv = tmp_path / "selection_log.csv"
    in_dir.mkdir()

    (in_dir / "karar_01.txt").write_text(destek_text, encoding="utf-8", newline="\n")

    accepted_paths = run_topic_filter(in_dir, out_dir, log_path=log_csv, rejected_dir=rej_dir)
    assert len(accepted_paths) == 0
    assert (rej_dir / "karar_01.txt").exists()


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