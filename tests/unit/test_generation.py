import json

from trafikrag.adapters.llms.fake import FakeLLM
from trafikrag.domain.decision import Chunk, ScoredChunk
from trafikrag.generation.citation_check import check_statements
from trafikrag.generation.summarizer import summarize

CHUNKS = {
    "c1": Chunk(
        id="c1", decision_id="k1", section_kind="gerekce",
        text="Kusur raporunda davalının %70, davacının %30 kusurlu olduğu belirtilmiştir.",
    )
}


def _statement(**overrides):
    base = {
        "text": "Davalı %70 kusurlu bulunmuştur.",
        "chunk_id": "c1",
        "quote": "davalının %70, davacının %30 kusurlu",
    }
    return {**base, **overrides}


def test_valid_statement_passes():
    valid, warnings = check_statements([_statement()], CHUNKS)
    assert len(valid) == 1 and warnings == []


def test_unknown_chunk_is_rejected():
    valid, warnings = check_statements([_statement(chunk_id="c9")], CHUNKS)
    assert valid == [] and "parça" in warnings[0]


def test_fabricated_quote_is_rejected():
    valid, warnings = check_statements([_statement(quote="davalı tamamen kusursuzdur")], CHUNKS)
    assert valid == [] and "alıntı" in warnings[0]


def test_number_not_in_quote_is_rejected():
    valid, warnings = check_statements([_statement(text="Davalı %80 kusurlu bulunmuştur.")], CHUNKS)
    assert valid == [] and "rakam" in warnings[0]


SCORED = [ScoredChunk(chunk=CHUNKS["c1"], score=0.9)]


def _llm(statements):
    return FakeLLM(json.dumps({"statements": statements}))


def test_summarize_keeps_only_valid_statements():
    llm = _llm([_statement(), _statement(quote="davalı tamamen kusursuzdur")])
    summary, citations, warnings = summarize("yaya kazası", SCORED, llm)
    assert summary == "Davalı %70 kusurlu bulunmuştur. [1]"
    assert citations[0].decision_id == "k1" and citations[0].chunk_id == "c1"
    assert len(warnings) == 1


def test_summarize_with_no_valid_statement_returns_empty():
    summary, citations, warnings = summarize("yaya kazası", SCORED, _llm([_statement(chunk_id="c9")]))
    assert summary == "" and citations == []
    assert "kaynaklı özet üretilemedi" in warnings[-1]


def test_summarize_handles_bad_json():
    summary, citations, warnings = summarize("yaya kazası", SCORED, FakeLLM("json değil"))
    assert summary == "" and warnings == ["özet JSON'u çözülemedi"]


def test_summarize_without_chunks_skips_llm():
    class ExplodingLLM:
        def complete(self, *args, **kwargs):
            raise AssertionError("LLM çağrılmamalıydı")

    summary, citations, warnings = summarize("yaya kazası", [], ExplodingLLM())
    assert summary == "" and warnings == ["Benzer karar parçası bulunamadı"]