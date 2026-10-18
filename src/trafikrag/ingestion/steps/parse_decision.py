"""Ham karar metnini Decision nesnesine çevirir: künye alanları + bölümler."""
from __future__ import annotations

import re
from pathlib import Path

from trafikrag.domain.decision import Decision, Section

# "IV. GEREKÇE" gibi Romen rakamlı veya "C. Gerekçe" gibi harfli kısa başlıklar
ROMAN_HEADING = re.compile(r"^[IVX]+\.\s+(.{2,60})$")
LETTER_HEADING = re.compile(r"^[A-ZÇĞİÖŞÜ]\.\s+(.{2,60})$")
# Başlıksız eski kararlarda hüküm "SONUÇ :" ile başlar
SONUC_LINE = re.compile(r"^SONUÇ\s*:")


def _tr_lower(text: str) -> str:
    # Python'un lower()'ı "İ" ve "I" harflerini Türkçe'ye göre çevirmez
    return text.replace("İ", "i").replace("I", "ı").lower()


def _heading_kind(line: str) -> str | None:
    """Satır bir bölüm başlığıysa türünü döndürür, değilse None."""
    if SONUC_LINE.match(line):
        return "hukum"
    match = ROMAN_HEADING.match(line) or LETTER_HEADING.match(line)
    if not match:
        return None
    title = _tr_lower(match.group(1)).strip(" :")
    if title == "gerekçe":
        return "gerekce"
    if title in ("karar", "sonuç"):
        return "hukum"
    return None  # DAVA, CEVAP, TEMYİZ gibi başlıklar olay bölümünün içinde kalır


def split_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    buffer: list[str] = []
    current = "olay"  # ilk başlığa kadar olan her şey (künye dahil) olay sayılır

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            sections.append(Section(kind=current, text=body))

    for line in text.splitlines():
        kind = _heading_kind(line.strip())
        if kind and kind != current:
            flush()
            buffer.clear()
            current = kind
        buffer.append(line)
    flush()
    return sections


def _first(patterns: list[str], text: str) -> str:
    """Desenleri sırayla dener, ilk eşleşen grubu döndürür; hiçbiri uymazsa boş string."""
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""  # for döngüsünün DIŞINDA: tüm desenler denendikten sonra


def extract_metadata(text: str) -> dict:
    esas = _first([r"Esas No\s*:\s*(\d{4}/\d+)", r"(\d{4}/\d+)\s*\.?\s*E\b"], text)
    karar = _first([r"Karar No\s*:\s*(\d{4}/\d+)", r"(\d{4}/\d+)\s*\.?\s*K\b"], text)
    # re.I: "4. HUKUK DAİRESİ" ve "4. Hukuk Dairesi" yazımlarının ikisi de yakalansın
    daire = re.search(r"(\d+)\.\s*Hukuk\s+Da.res.", text, re.I)
    court = f"Yargıtay {daire.group(1)}. Hukuk Dairesi" if daire else ""
    # Kararın tarihi metnin sonunda: "... 30.05.2024 tarihinde oy birliğiyle karar verildi"
    dates = re.findall(r"(\d{2})[./](\d{2})[./](\d{4})\s+(?:tarihinde|gününde)", text)
    iso = f"{dates[-1][2]}-{dates[-1][1]}-{dates[-1][0]}" if dates else ""
    return {"court": court, "esas_no": esas, "karar_no": karar, "date": iso}


def parse_decision(text: str, decision_id: str) -> Decision:
    meta = extract_metadata(text)
    return Decision(
        id=decision_id,
        court=meta["court"],
        esas_no=meta["esas_no"],
        karar_no=meta["karar_no"],
        date=meta["date"],
        source_url="",
        sections=split_sections(text),
    )


def load_decision(path: Path) -> Decision:
    return parse_decision(path.read_text(encoding="utf-8"), decision_id=path.stem)
