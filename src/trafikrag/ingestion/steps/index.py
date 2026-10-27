"""6. Adım (index): Decision nesnelerini diske data/interim/decisions.jsonl olarak yazar."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from trafikrag.domain.decision import Decision


def write_decisions_jsonl(decisions: list[Decision], output_path: Path) -> Path:
    """Decision nesnesi listesini JSONL (satır tabanlı JSON) formatında yazar (idempotent)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for dec in decisions:
            f.write(json.dumps(asdict(dec), ensure_ascii=False) + "\n")
    return output_path