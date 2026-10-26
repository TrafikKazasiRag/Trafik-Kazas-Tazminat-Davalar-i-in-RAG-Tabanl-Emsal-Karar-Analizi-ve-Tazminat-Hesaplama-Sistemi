"""Yalnızca verilen parçalara dayanan kaynaklı özet."""
import json
from pathlib import Path

from trafikrag.domain.analysis import Citation
from trafikrag.domain.decision import ScoredChunk
from trafikrag.extraction.extractor import load_prompt
from trafikrag.generation.citation_check import check_statements
from trafikrag.ports.llm import LLM

PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "summarize_with_citations.v1.md"

SUMMARY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "statements": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "chunk_id": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["text", "chunk_id", "quote"],
            },
        },
    },
    "required": ["statements"],
}


def format_chunks(scored_chunks: list[ScoredChunk]) -> str:
    blocks = []
    for scored in scored_chunks:
        chunk = scored.chunk
        header = f"[chunk_id={chunk.id} | karar={chunk.decision_id} | bölüm={chunk.section_kind}]"
        blocks.append(f"{header}\n{chunk.text}")
    return "\n\n".join(blocks)


def summarize(case_text: str, scored_chunks: list[ScoredChunk], llm: LLM) -> tuple[str, list[Citation], list[str]]:
    """(özet, atıflar, uyarılar) döner. Denetimden geçmeyen ifadeler özete girmez."""
    if not scored_chunks:
        return "", [], ["Benzer karar parçası bulunamadı"]
    system, user_template = load_prompt(PROMPT_PATH)
    prompt = user_template.replace("{chunks}", format_chunks(scored_chunks)).replace("{case_text}", case_text)
    raw = llm.complete(prompt, system=system, json_schema=SUMMARY_SCHEMA)
    try:
        statements = json.loads(raw).get("statements") or []
    except (json.JSONDecodeError, AttributeError):
        return "", [], ["özet JSON'u çözülemedi"]

    chunks = {scored.chunk.id: scored.chunk for scored in scored_chunks}
    valid, warnings = check_statements(statements, chunks)
    if not valid:
        warnings.append("Doğrulanmış ifade kalmadı; kaynaklı özet üretilemedi")
        return "", [], warnings

    lines: list[str] = []
    citations: list[Citation] = []
    for number, statement in enumerate(valid, start=1):
        chunk = chunks[statement["chunk_id"]]
        lines.append(f"{statement['text']} [{number}]")
        citations.append(Citation(decision_id=chunk.decision_id, chunk_id=chunk.id, quote=statement["quote"]))
    return "\n".join(lines), citations, warnings