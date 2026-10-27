"""5. Adım (split): Metni parse_decision.py kullanarak Decision veri nesnesine dönüştürür.

Yanındaki karar_NN.meta.json dosyasından source_url bilgisini okur ve
bölümleri (olay, gerekce, hukum) veya künyesi eksik olan kararları raporlar.
"""
from __future__ import annotations

import json
from pathlib import Path

from trafikrag.domain.decision import Decision
from trafikrag.ingestion.steps.parse_decision import parse_decision


def read_source_url_from_meta(txt_path: Path, raw_dir: Path | None = None) -> str:
    """Karar dosyasının yanındaki veya raw_dir içindeki .meta.json dosyasından source_url okur."""
    candidates = [txt_path.with_suffix(".meta.json")]
    if raw_dir is not None:
        candidates.append(raw_dir / f"{txt_path.stem}.meta.json")

    for meta_path in candidates:
        if meta_path.exists():
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                url = data.get("source_url", "")
                if isinstance(url, str) and url.strip():
                    return url.strip()
            except (json.JSONDecodeError, OSError):
                continue
    return ""


def has_complete_sections(decision: Decision) -> bool:
    """Kararda olay, gerekce ve hukum bölümlerinin üçünün de bulunup bulunmadığını kontrol eder."""
    kinds = {sec.kind for sec in decision.sections}
    return {"olay", "gerekce", "hukum"}.issubset(kinds)


def split_decision_file(
    path: Path,
    source_url: str = "",
    raw_dir: Path | None = None,
) -> Decision:
    """Tek bir karar dosyasını okuyup Decision alanlarına ve bölümlerine ayırır."""
    text = path.read_text(encoding="utf-8")
    decision = parse_decision(text, decision_id=path.stem)
    resolved_url = source_url or read_source_url_from_meta(path, raw_dir=raw_dir)
    if resolved_url:
        decision.source_url = resolved_url
    return decision


def split_decisions_dir(
    input_dir: Path,
    source_urls: dict[str, str] | None = None,
    raw_dir: Path | None = None,
) -> list[Decision]:
    """Klasördeki tüm karar_*.txt dosyalarını Decision nesnelerine dönüştürür."""
    if source_urls is None:
        source_urls = {}

    decisions: list[Decision] = []
    for path in sorted(input_dir.glob("karar_*.txt")):
        url = source_urls.get(path.stem, "")
        decisions.append(split_decision_file(path, source_url=url, raw_dir=raw_dir))
    return decisions