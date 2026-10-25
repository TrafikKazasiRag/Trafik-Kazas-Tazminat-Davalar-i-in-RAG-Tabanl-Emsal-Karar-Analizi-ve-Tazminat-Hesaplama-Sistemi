"""Tek bir karar üzerinde extract_facts'i gerçek Claude ile dener.

Kullanım: python scripts/try_extract.py data/txt_dosyalar/karar_1.txt
"""

import os
import sys
from pathlib import Path

from trafikrag.adapters.llms.claude import ClaudeLLM
from trafikrag.adapters.llms.local import LocalLLM
from trafikrag.extraction.extractor import extract_facts
from trafikrag.ingestion.steps.clean import clean_text

def load_env(path: str=".env") -> None:
    if not Path(path).exists():
        return
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and not line.startswith("#") and value.strip():
            os.environ.setdefault(key.strip(), value.strip())

def main() -> None:
    load_env()
    path = Path(sys.argv[1])
    text = clean_text(path.read_text(encoding="utf-8"))
    #facts, warnings = extract_facts(path.stem, text, ClaudeLLM())
    backend = sys.argv[2] if len(sys.argv) > 2 else "claude"
    llm = LocalLLM(model=sys.argv[3]) if backend == "local" else ClaudeLLM()
    facts, warnings = extract_facts(path.stem, text, llm)
    print("--- ALANLAR ---")
    for name in ("plaintiff_fault", "defendant_fault", "disability_rate", "injury_type", "awarded_items", "outcome"):
        print(f"{name}: {getattr(facts, name)}")
    print("--- KANIT ---")
    for key, quote in facts.evidence.items():
        print(f"{key}: {quote[:150]}")
    print("--- UYARILAR ---")
    for warning in warnings:
        print(warning)


if __name__ == "__main__":
    main()