from pathlib import Path

import pytest

from trafikrag.ingestion.steps.parse_decision import load_decision, parse_decision

EMSAL = """SIRA NO: 1
DOKÜMAN ID: 123
DAİRE / MAHKEME: Antalya Bölge Adliye Mahkemesi 4. Hukuk Dairesi
ESAS NO: 2021/23
KARAR NO: 2023/335
KARAR TARİHİ: 16.03.2023
İÇERİK HASH (MD5): abc
=======================================================

T.C.
BÖLGE ADLİYE MAHKEMESİ
DAVA : Maddi Tazminat
Davacı yaralandı, maluliyet tespit edildi.
G E R E K Ç E
Kusur oranı bilirkişi raporuna göre belirlendi.
HÜKÜM : Yukarıda açıklanan nedenlerle istinaf başvurusunun reddine,
"""


def test_header_metadata_is_read():
    d = parse_decision(EMSAL, "karar_1")
    assert d.court == "Antalya Bölge Adliye Mahkemesi 4. Hukuk Dairesi"
    assert (d.esas_no, d.karar_no, d.date) == ("2021/23", "2023/335", "2023-03-16")
    assert d.source_url == "uyap-emsal:123"


def test_spaced_and_inline_headings_split_sections():
    d = parse_decision(EMSAL, "karar_1")
    assert [s.kind for s in d.sections] == ["olay", "gerekce", "hukum"]
    assert d.sections[2].text.startswith("HÜKÜM")


def test_karar_word_in_narrative_is_not_a_heading():
    text = EMSAL.replace("T.C.", "KARAR Davacılar vekili dava dilekçesinde özetle")
    d = parse_decision(text, "x")
    assert [s.kind for s in d.sections] == ["olay", "gerekce", "hukum"]
    assert "Davacılar vekili" in d.sections[0].text


DATA = Path("data/txt_dosyalar")


@pytest.mark.skipif(not DATA.exists(), reason="data/txt_dosyalar yok")
def test_all_real_decisions_have_metadata_and_hukum():
    files = sorted(DATA.glob("karar_*.txt"))
    assert files
    no_hukum = 0
    for path in files:
        d = load_decision(path)
        assert d.court and d.esas_no and d.karar_no and d.date, path.name
        if "hukum" not in [s.kind for s in d.sections]:
            no_hukum += 1
    assert no_hukum / len(files) < 0.05