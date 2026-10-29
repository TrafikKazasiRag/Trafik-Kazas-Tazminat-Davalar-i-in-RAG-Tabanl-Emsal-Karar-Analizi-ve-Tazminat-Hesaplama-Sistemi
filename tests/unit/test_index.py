"""test_index.py: Karar/chunk konu etiketleme (multi-label) ve indeksleme adımının birim testleri."""
import json
from pathlib import Path

from trafikrag.domain.decision import Decision, Section
from trafikrag.ingestion.steps.index import (
    build_chunk_metadata,
    extract_decision_topics,
    index_decision,
    write_decisions_jsonl,
)


def test_write_decisions_jsonl_creates_valid_file(tmp_path: Path) -> None:
    """write_decisions_jsonl fonksiyonunun geçerli JSONL dosyası ürettiğini ve 'topics' alanını doğrular."""
    decision = Decision(
        id="karar_01",
        court="Ankara Asliye Hukuk Mahkemesi",
        esas_no="2023/100",
        karar_no="2023/200",
        date="2023-01-01",
        source_url="https://ornek.com/karar_01",
        sections=[
            Section(kind="olay", text="Trafik kazası gerçekleşmiştir."),
            Section(kind="hukum", text="Geçici iş göremezlik tazminatının kabulüne karar verildi."),
        ],
    )

    output_file = tmp_path / "decisions.jsonl"
    write_decisions_jsonl([decision], output_file)

    assert output_file.exists()
    lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    saved_data = json.loads(lines[0])
    assert saved_data["id"] == "karar_01"
    assert saved_data["court"] == "Ankara Asliye Hukuk Mahkemesi"
    assert "topics" in saved_data
    assert saved_data["topics"] == ["yaralanma"]
    assert len(saved_data["sections"]) == 2


def test_chunk_metadata_includes_topics_list() -> None:
    """Her chunk'ın metadata['topics'] alanına karar konusunun liste olarak yazıldığını doğrular."""
    decision = Decision(
        id="k_test_01",
        court="Ankara BAM 26. Hukuk Dairesi",
        esas_no="2023/100",
        karar_no="2023/200",
        date="2023-05-10",
        source_url="",
        sections=[
            Section(kind="hukum", text="Sürekli iş göremezlik tazminatının davalıdan tahsiline karar verildi.")
        ],
    )

    chunks = index_decision(decision)

    assert len(chunks) == 1
    assert "topics" in chunks[0]["metadata"]
    assert chunks[0]["metadata"]["topics"] == ["yaralanma"]


def test_topics_carried_to_all_chunks_of_decision() -> None:
    """Karar düzeyindeki 'topics' etiketinin o karara ait tüm chunk'lara taşındığını doğrular."""
    decision = Decision(
        id="k_test_02",
        court="Ankara Asliye Hukuk Mahkemesi",
        esas_no="2022/10",
        karar_no="2022/20",
        date="2022-01-01",
        source_url="",
        sections=[
            Section(kind="olay", text="Davacı yaralanmalı kaza nedeniyle tazminat istemiştir."),
            Section(kind="gerekce", text="Maluliyet oranı %20 hesaplanmıştır."),
            Section(kind="hukum", text="Davanın kabulüne karar verilmiştir."),
        ],
    )

    chunks = index_decision(decision)

    assert len(chunks) == 3
    for chunk in chunks:
        assert chunk["metadata"]["topics"] == ["yaralanma"]


def test_topic_classification_death_and_other_examples() -> None:
    """Ölüm, yaralanma, hasar ve diğer konu örneklerinin doğru etiketlendiğini doğrular."""
    d_olum = Decision(
        id="k_olum", court="", esas_no="", karar_no="", date="", source_url="",
        sections=[Section(kind="hukum", text="Destekten yoksun kalma tazminatına karar verilmiştir.")]
    )
    assert extract_decision_topics(d_olum) == ["olum"]

    d_hasar = Decision(
        id="k_hasar", court="", esas_no="", karar_no="", date="", source_url="",
        sections=[Section(kind="hukum", text="Araç değer kaybı ve onarım bedelinin tahsiline.")]
    )
    assert extract_decision_topics(d_hasar) == ["hasar"]

    d_diger = Decision(
        id="k_diger", court="", esas_no="", karar_no="", date="", source_url="",
        sections=[Section(kind="hukum", text="Görevsizlik nedeniyle davanın usulden reddine.")]
    )
    assert extract_decision_topics(d_diger) == ["diger"]