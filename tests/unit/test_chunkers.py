from pathlib import Path

import pytest

from trafikrag.adapters.chunkers.by_section import BySectionChunker, split_text
from trafikrag.adapters.chunkers.fixed_size import FixedSizeChunker
from trafikrag.ingestion.steps.parse_decision import load_decision, parse_decision

SAMPLE = """T.C.
YARGITAY
4. HUKUK DAİRESİ
Esas No : 2024/1
Karar No : 2024/2
I. DAVA
Davacı yaralandı.
II. CEVAP
Davalı davanın reddini istedi.
IV. GEREKÇE
Kusur oranı bilirkişiden alınmalıdır.
V. KARAR
BOZULMASINA,
30.05.2024 tarihinde oy birliğiyle karar verildi.
"""

def test_parser_finds_three_sections_and_metadata():
    d = parse_decision(SAMPLE, "x")
    assert [s.kind for s in d.sections] == ["olay", "gerekce", "hukum"]
    assert (d.esas_no, d.karar_no, d.date) == ("2024/1", "2024/2", "2024-05-30")
    assert d.court == "Yargıtay 4. Hukuk Dairesi"
def test_by_section_never_mixes_sections():
    chunks = BySectionChunker(max_tokens=400).chunk(parse_decision(SAMPLE, "x"))
    assert {c.section_kind for c in chunks} == {"olay", "gerekce", "hukum"}
    assert len({c.id for c in chunks}) == len(chunks)


def test_long_section_is_split():
    pieces = split_text("kelime " * 100, max_words=30)
    assert len(pieces) == 4 and all(len(p.split()) <= 30 for p in pieces)


def test_fixed_size_has_overlap():
    d = parse_decision("kelime " * 100, "x")
    chunker = FixedSizeChunker(size_tokens=48, overlap_tokens=16)  # 30 ve 10 sözcük
    chunks = chunker.chunk(d)
    assert len(chunks) >= 3
    assert chunks[0].text.split()[-10:] == chunks[1].text.split()[:10]


RAW = Path("data/raw/karar_03.txt")


@pytest.mark.skipif(not RAW.exists(), reason="data/raw git'e girmez, yerelde çalışır")
def test_real_decision_has_all_sections():
    d = load_decision(RAW)
    assert [s.kind for s in d.sections] == ["olay", "gerekce", "hukum"]
    assert d.esas_no == "2023/11230" and d.karar_no == "2023/13550"