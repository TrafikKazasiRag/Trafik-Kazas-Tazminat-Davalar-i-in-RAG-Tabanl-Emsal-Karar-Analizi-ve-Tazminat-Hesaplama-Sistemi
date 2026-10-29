"""test_index.py: Karar/chunk konu etiketleme (multi-label) adımının birim testleri."""
from trafikrag.domain.decision import Decision, Section
from trafikrag.ingestion.steps.index import build_chunk_metadata, extract_decision_topics, index_decision


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