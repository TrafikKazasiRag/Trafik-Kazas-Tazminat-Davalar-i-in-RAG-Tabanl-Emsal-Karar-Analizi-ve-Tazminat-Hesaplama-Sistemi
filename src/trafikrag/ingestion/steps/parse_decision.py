"""Ham karar metnini Decision nesnesine çevirir: künye alanları + bölümler.

İki biçimi destekler:
1. UYAP Emsal dosyaları: başta "DAİRE / MAHKEME:", "ESAS NO:" gibi bir künye bloğu ve
   ardından "=====" çizgisi bulunur. Künye bu bloktan okunur.
2. Künye bloğu olmayan metinler (karar_01..03): künye metinden regex ile çıkarılır.
"""
from __future__ import annotations

import re
from pathlib import Path

from trafikrag.domain.decision import Decision, Section

# "IV. GEREKÇE" gibi Romen rakamlı veya "C. Gerekçe" gibi harfli kısa başlıklar
ROMAN_HEADING = re.compile(r"^[IVX]+\.\s+(.{2,60})$")
LETTER_HEADING = re.compile(r"^[A-ZÇĞİÖŞÜ]\.\s+(.{2,60})$")
# Başlıksız eski kararlarda hüküm "SONUÇ :" ile başlar
SONUC_LINE = re.compile(r"^SONUÇ\s*:")
# "G E R E K Ç E" gibi harfleri aralıklı yazılmış başlıklar
SPACED_LETTERS = re.compile(r"^(?:\S ){2,}\S$")
# Tek başına duran başlıklar (küçük harfe çevrilmiş ve ":" atılmış hâlleri)
GEREKCE_TITLES = {"gerekçe", "delillerin değerlendirilmesi ve gerekçe", "gereği düşünüldü"}
HUKUM_TITLES = {"hüküm", "sonuç ve hüküm"}
# "Yukarıda açıklanan nedenlerle ..." ile başlayan hüküm cümleleri (başlığı olmayan kararlar için)
HUKUM_OPENING = re.compile(r"^Yukarıda (?:açıklanan|yazılı|belirtilen) ", re.IGNORECASE)

# "HÜKÜM : Gerekçesi yukarıda ..." gibi başlığın aynı satırda metinle devam ettiği hüküm başlıkları
HUKUM_PREFIX = re.compile(r"^(?:H\s?Ü\s?K\s?Ü\s?M|Hüküm)\s*[:/](?!\s*KARAR)")

# "KARAR:Yukarıda ..." / "K A R AR / Gerekçe uyarınca" / "GEREĞİ DÜŞÜNÜLDÜ/ Gerekçe uyarınca" gibi
# hükmün başlıkla aynı satırda başladığı durumlar (iki nokta veya eğik çizgiden sonra)
INLINE_HUKUM = re.compile(r"^(?:KARAR|GEREĞİ DÜŞÜNÜLDÜ)\s*[:/]\s*(?:Yukarıda|Gerekçe)")
# "GEREĞİ DÜŞÜNÜLDÜ: Davacı vekili ..." gibi gerekçenin başlıkla aynı satırda başladığı durumlar
INLINE_GEREKCE = re.compile(r"^GEREĞİ DÜŞÜNÜLDÜ\s*:")

HEADER_SEPARATOR = re.compile(r"^={10,}\s*$", re.MULTILINE)


def _tr_lower(text: str) -> str:
    # Python'un lower()'ı "İ" ve "I" harflerini Türkçe'ye göre çevirmez
    return text.replace("İ", "i").replace("I", "ı").lower()


def _squash(line: str) -> str:
    """'G E R E K Ç E :' -> 'GEREKÇE:'. Aralıklı yazılmamış satırlara dokunmaz."""
    line = line.strip()
    core = line.rstrip(" :;/")
    if SPACED_LETTERS.match(core):
        return core.replace(" ", "") + line[len(core):].strip()
    return line


def _heading_kind(line: str) -> str | None:
    """Satır bir bölüm başlığıysa türünü döndürür, değilse None."""
    if HUKUM_PREFIX.match(line):
        return "hukum"
    # "K A R AR / Gerekçe ..." gibi aralıklı yazılanlar için ilk 14 karakterin boşlukları atılır
    head = re.sub(r"\s+", "", line[:14]) + line[14:]
    if INLINE_HUKUM.match(head) or INLINE_HUKUM.match(line):
        return "hukum"
    if INLINE_GEREKCE.match(line):
        return "gerekce"
    line = _squash(line)
    if SONUC_LINE.match(line):
        return "hukum"
    bare = _tr_lower(line).strip(" :;/")
    if bare in GEREKCE_TITLES:
        return "gerekce"
    if bare in HUKUM_TITLES:
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
    lines = text.splitlines()
    kinds = [_heading_kind(line.strip()) for line in lines]
    # Başlığı olmayan kararlarda hükmü "Yukarıda açıklanan nedenlerle ..." cümlesinden başlat
    if "hukum" not in kinds:
        for index in range(len(lines) - 1, -1, -1):
            if HUKUM_OPENING.match(lines[index].strip()):
                kinds[index] = "hukum"
                break

    sections: list[Section] = []
    buffer: list[str] = []
    current = "olay"  # ilk başlığa kadar olan her şey olay sayılır

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            sections.append(Section(kind=current, text=body))

    for line, kind in zip(lines, kinds):
        if kind and kind != current:
            flush()
            buffer.clear()
            current = kind
        buffer.append(line)
    flush()
    return sections


def split_header(text: str) -> tuple[dict, str]:
    """UYAP Emsal künye bloğunu ayırır. Blok yoksa ({}, text) döner."""
    match = HEADER_SEPARATOR.search(text)
    if not match or match.start() > 1500:
        return {}, text
    fields: dict[str, str] = {}
    for line in text[: match.start()].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip().upper()] = value.strip()
    if "DAİRE / MAHKEME" not in fields:
        return {}, text
    return fields, text[match.end():].lstrip("\n")


def _first(patterns: list[str], text: str) -> str:
    """Desenleri sırayla dener, ilk eşleşen grubu döndürür; hiçbiri uymazsa boş string."""
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""  # for döngüsünün DIŞINDA: tüm desenler denendikten sonra


def _iso_date(value: str) -> str:
    match = re.search(r"(\d{2})[./](\d{2})[./](\d{4})", value)
    return f"{match.group(3)}-{match.group(2)}-{match.group(1)}" if match else ""


def metadata_from_header(fields: dict) -> dict:
    doc_id = fields.get("DOKÜMAN ID", "")
    return {
        "court": fields.get("DAİRE / MAHKEME", ""),
        "esas_no": _first([r"(\d{4}/\d+)"], fields.get("ESAS NO", "")),
        "karar_no": _first([r"(\d{4}/\d+)"], fields.get("KARAR NO", "")),
        "date": _iso_date(fields.get("KARAR TARİHİ", "")),
        "source_url": f"uyap-emsal:{doc_id}" if doc_id else "",
    }


def extract_metadata(text: str) -> dict:
    fields, _ = split_header(text)
    if fields:
        return metadata_from_header(fields)
    esas = _first([r"Esas No\s*:\s*(\d{4}/\d+)", r"(\d{4}/\d+)\s*\.?\s*E\b"], text)
    karar = _first([r"Karar No\s*:\s*(\d{4}/\d+)", r"(\d{4}/\d+)\s*\.?\s*K\b"], text)
    # re.I: "4. HUKUK DAİRESİ" ve "4. Hukuk Dairesi" yazımlarının ikisi de yakalansın
    daire = re.search(r"(\d+)\.\s*Hukuk\s+Da.res.", text, re.IGNORECASE)
    court = f"Yargıtay {daire.group(1)}. Hukuk Dairesi" if daire else ""
    # Kararın tarihi metnin sonunda: "... 30.05.2024 tarihinde oy birliğiyle karar verildi"
    dates = re.findall(r"(\d{2})[./](\d{2})[./](\d{4})\s+(?:tarihinde|gününde)", text)
    iso = f"{dates[-1][2]}-{dates[-1][1]}-{dates[-1][0]}" if dates else ""
    return {"court": court, "esas_no": esas, "karar_no": karar, "date": iso, "source_url": ""}


def parse_decision(text: str, decision_id: str) -> Decision:
    fields, body = split_header(text)
    meta = metadata_from_header(fields) if fields else extract_metadata(text)
    return Decision(
        id=decision_id,
        court=meta["court"],
        esas_no=meta["esas_no"],
        karar_no=meta["karar_no"],
        date=meta["date"],
        source_url=meta["source_url"],
        sections=split_sections(body),
    )


def load_decision(path: Path) -> Decision:
    return parse_decision(path.read_text(encoding="utf-8"), decision_id=path.stem)