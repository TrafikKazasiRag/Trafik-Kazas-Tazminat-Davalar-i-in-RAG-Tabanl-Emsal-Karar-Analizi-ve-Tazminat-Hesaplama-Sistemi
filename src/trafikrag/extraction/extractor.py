"""Karardan yapılandırılmış alan çıkarımı (LLM + doğrulama)."""

import json
from pathlib import Path

from trafikrag.domain.facts import ExtractedFacts
from trafikrag.extraction.validators import validate_facts
from trafikrag.ports.llm import LLM


FACTS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "plaintiff_fault": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "defendant_fault": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "disability_rate": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "injury_type": {"type": ["string", "null"]},
        "awarded_items": {
            "type": "object",
            "propertyNames": {"enum": [
                "surekli_isgoremezlik", "gecici_isgoremezlik",
                "bakici_gideri", "tedavi_gideri", "manevi_tazminat", "diger"]},
            "additionalProperties": {"type": "number", "minimum": 0},
        },
        "outcome": {"enum": ["kabul", "kismen_kabul", "ret", "bozma", "istinaf_reddi", "kaldirma", None]},
        "evidence": {"type": "object", "additionalProperties": {"type": "string"}},
    },
    "required": ["plaintiff_fault", "defendant_fault", "disability_rate",
                 "injury_type", "awarded_items", "outcome", "evidence"],
}


PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "extract_facts.v1.md"

def load_prompt(path: Path = PROMPT_PATH) -> tuple[str,str]:
    """Prompt dosyasından (system, user_şablonu) çifti döner."""
    text = path.read_text(encoding="utf-8")
    body = text.split("## SYSTEM", 1)[1]
    system, user_template = body.split("## USER", 1)
    return system.strip(), user_template.strip()
def extract_facts(decision_id: str, decision_text: str, llm: LLM)-> tuple[ExtractedFacts, list[str]]:
    system, user_template = load_prompt()
    prompt = user_template.replace("{decision_id}", decision_id).replace("{decision_text}", decision_text)
    raw = llm.complete(prompt, system=system, json_schema=FACTS_SCHEMA)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ExtractedFacts(decision_id=decision_id), ["json çözülemedi"]
    facts = ExtractedFacts(
        decision_id = decision_id,
        plaintiff_fault=data.get("plaintiff_fault"),
        defendant_fault=data.get("defendant_fault"),
        disability_rate=data.get("disability_rate"),
        injury_type=data.get("injury_type"),
        awarded_items=data.get("awarded_items") or {},
        outcome=data.get("outcome"),
        evidence=data.get("evidence") or {},
    )
    return validate_facts(facts, decision_text)