"""Karar konusu sınıflandırması: kural tabanlı, LLM'siz. Retriever'da metadata filtresi olarak kullanılır."""

import re

from trafikrag.domain.decision import Decision

TOPICS = ("olum", "yaralanma", "hasar", "diger")

OLUM = re.compile(r"destekten yoksun")
YARALANMA = re.compile(r"sürekli iş göremezlik|maluliyet|geçici iş göremezlik|bakıcı gideri")
HASAR = re.compile(r"değer kayb|araç hasar|hasar bedeli|onarım bedeli")

def _lower(text: str) -> str:
    # Python'un lower()'ı "İ" ve "I" harflerini Türkçe'ye göre çevirmez
    return text.replace("İ", "i").replace("I", "ı").lower()

def _section_text(decision: Decision, kinds: tuple[str, ...]) -> str:
    return _lower("\n".join(s.text for s in decision.sections if s.kind in kinds))


def _counts(text: str) -> tuple[int, int]:
    return len(OLUM.findall(text)), len(YARALANMA.findall(text))


def classify_topic(decision: Decision) -> str:
    hukum = _section_text(decision, ("hukum",))
    olum_h, yar_h = _counts(hukum)
    if olum_h or yar_h:  # hükümde kalem adı geçiyorsa hüküm belirler
        return "olum" if olum_h >= yar_h else "yaralanma"

    # hükümde kalem yok (örn. istinaf reddi): gerekçeye bak; hiç bölüm yoksa tüm metin
    gerekce = _section_text(decision, ("gerekce",)) or _section_text(decision, ("olay", "gerekce", "hukum"))
    olum_g, yar_g = _counts(gerekce)
    if olum_g >= 2 and olum_g * 3 >= yar_g:  # geçerken anılan "destekten yoksun" sayılmaz
        return "olum"
    if yar_g >= 1:
        return "yaralanma"
    if HASAR.search(hukum + gerekce):
        return "hasar"
    return "diger"