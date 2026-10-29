"""runner.py uçtan uca veri hattı ve kalite kontrol raporu birim testleri."""
import json
from pathlib import Path

from trafikrag.ingestion.runner import run_pipeline


def test_runner_executes_configured_steps_and_generates_summary_report(tmp_path: Path) -> None:
    raw_dir = tmp_path / "data" / "raw"
    interim_dir = tmp_path / "data" / "interim"
    raw_dir.mkdir(parents=True)

    # 1. Geçerli karar + yan .meta.json dosyası + site gürültüsü
    valid_decision = (
        "Ankara Avukat - Minval Hukuk Bürosu\n"
        "Trafik Kazası Tazminatı Hesaplama için TIKLAYINIZ\n"
        "Yargıtay 4. Hukuk Dairesi\n"
        "Esas No: 2023/11230\n"
        "Karar No: 2023/13550\n"
        "I. DAVA\n"
        "Davacı Ahmet Yılmaz (TC: 12345678901) vekili, 06 ABC 123 plakalı aracın karıştığı "
        "yaralanmalı trafik kazası nedeniyle sürekli iş göremezlik ve bakıcı gideri tazminatı istemiştir.\n"
        "IV. GEREKÇE\n"
        "Bilirkişi raporunda davalı sürücü %75 kusurlu bulunmuş, maluliyet oranı %15 tespit edilmiştir.\n"
        "V. KARAR\n"
        "SONUÇ : Hükmün BOZULMASINA, 14.12.2023 tarihinde oy birliğiyle karar verildi.\n"
    )
    (raw_dir / "karar_01.txt").write_text(valid_decision, encoding="utf-8", newline="\n")
    (raw_dir / "karar_01.meta.json").write_text(
        json.dumps({"source_url": "https://ornek.com/karar_01", "source_site": "ornek"}),
        encoding="utf-8",
    )

    # 2. Mükerrer karar (karar_01 ile aynı Esas/Karar No ama daha kısa -> dedupe adımında elenmeli)
    duplicate_decision = (
        "Yargıtay 4. Hukuk Dairesi\n"
        "Esas No: 2023/11230\n"
        "Karar No: 2023/13550\n"
        "I. DAVA\nKısa özet metin.\n"
    )
    (raw_dir / "karar_02.txt").write_text(duplicate_decision, encoding="utf-8", newline="\n")

    # 3. Kapsam dışı ceza kararı (topic_filter adımında elenmeli)
    criminal_decision = (
        "Yargıtay 12. Ceza Dairesi\n"
        "Esas No: 2022/500\n"
        "Karar No: 2022/600\n"
        "Taksirle yaralama suçundan sanığın mahkumiyetine dair hükmün ONANMASINA, 10.05.2022 tarihinde karar verildi.\n"
    )
    (raw_dir / "karar_03.txt").write_text(criminal_decision, encoding="utf-8", newline="\n")

    # 4. Kapsam dışı ölümlü kaza kararı (topic_filter adımında ayrı rejected_dir'e atılmalı)
    fatal_decision = (
        "Yargıtay 4. Hukuk Dairesi\n"
        "Esas No: 2023/9999\n"
        "Karar No: 2023/8888\n"
        "Meydana gelen ölümlü trafik kazası neticesinde destekten yoksun kalma tazminatı talep edilmiştir.\n"
    )
    (raw_dir / "karar_04.txt").write_text(fatal_decision, encoding="utf-8", newline="\n")

    config = {
        "ingestion": {
            "steps": ["clean", "dedupe", "topic_filter", "split", "index"],
            "raw_dir": str(raw_dir),
            "interim_dir": str(interim_dir),
        }
    }

    report = run_pipeline(config)

    # Toplu kontrol raporu doğrulamaları (Bölüm 6)
    assert report.total_raw == 4
    assert report.eliminated_by_step["dedupe"] == 1
    assert report.eliminated_by_step["topic_filter"] == 2  # 1 ceza, 1 ölümlü elendi
    assert report.final_count == 1
    assert report.complete_sections_ratio == 1.0
    assert report.outcome_distribution.get("bozma") == 1
    assert report.year_distribution.get("2023") == 1

    # Ölümlü kaza kararının rejected_dir'e gittiğinin doğrulanması
    rejected_dir = interim_dir / "work" / "03_rejected_olumlu"
    assert (rejected_dir / "karar_04.txt").exists()

    # Çıktı dosyası (decisions.jsonl) doğrulamaları
    jsonl_path = interim_dir / "decisions.jsonl"
    assert jsonl_path.exists()
    lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    saved_decision = json.loads(lines[0])
    assert saved_decision["id"] == "karar_01"
    assert saved_decision["source_url"] == "https://ornek.com/karar_01"
    assert saved_decision["esas_no"] == "2023/11230"

    # Gürültünün silindiği doğrulanmalı (anonymize kaldırıldığı için kişisel veriler korunur)
    all_section_text = "\n".join(s["text"] for s in saved_decision["sections"])
    assert "TIKLAYINIZ" not in all_section_text
    assert "Ahmet Yılmaz" in all_section_text
    assert "12345678901" in all_section_text

    # Idempotency: aynı hat ikinci kez çalıştırıldığında birebir aynı raporu ve çıktıyı üretmeli
    report_second = run_pipeline(config)
    assert report_second.final_count == report.final_count
    assert jsonl_path.read_text(encoding="utf-8") == "\n".join(lines) + "\n"