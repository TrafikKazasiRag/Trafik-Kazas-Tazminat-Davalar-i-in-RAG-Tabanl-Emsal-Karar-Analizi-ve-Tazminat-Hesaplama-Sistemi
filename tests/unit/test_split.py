"""split.py adımı için birim testler."""
from pathlib import Path
from trafikrag.ingestion.steps.split import split_decision_file, split_decisions_dir


def test_split_converts_text_to_decision_object(tmp_path: Path) -> None:
    sample_text = (
        "Yargıtay 4. Hukuk Dairesi\n"
        "Esas No: 2023/11230\n"
        "Karar No: 2023/13550\n"
        "I. DAVA\n"
        "Davacı vekili tazminat talep etmiştir.\n"
        "IV. GEREKÇE\n"
        "Bilirkişi kusur oranı %75'tir.\n"
        "V. KARAR\n"
        "SONUÇ : Onanmasına, 14.12.2023 tarihinde karar verildi.\n"
    )
    txt_file = tmp_path / "karar_03.txt"
    txt_file.write_text(sample_text, encoding="utf-8", newline="\n")

    decision = split_decision_file(txt_file, source_url="https://ornek.com/karar3")

    assert decision.id == "karar_03"
    assert decision.court == "Yargıtay 4. Hukuk Dairesi"
    assert decision.esas_no == "2023/11230"
    assert decision.karar_no == "2023/13550"
    assert decision.date == "2023-12-14"
    assert decision.source_url == "https://ornek.com/karar3"
    assert len(decision.sections) >= 3
    assert decision.sections[0].kind == "olay"