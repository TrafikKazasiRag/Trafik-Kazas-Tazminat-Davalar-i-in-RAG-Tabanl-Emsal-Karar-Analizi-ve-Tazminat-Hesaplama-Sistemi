"""LLM çıktısını koda güvenerek doğrular: uydurma alıntı, kusur toplamı, enum, tutar."""
import re

from trafikrag.domain.facts import ExtractedFacts

ALLOWED_ITEMS = {
    "surekli_isgoremezlik", "gecici_isgoremezlik",
    "bakici_gideri", "tedavi_gideri", "manevi_tazminat", "diger",
}
ALLOWED_OUTCOMES = {"kabul", "kismen_kabul", "ret", "bozma", "istinaf_reddi", "kaldirma"}
SIMPLE_FIELDS = ("plaintiff_fault", "defendant_fault", "disability_rate", "injury_type", "outcome")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _amount_in(text: str, amount: float) -> bool:
    """215180.2 -> '215.180,20' veya '215.180' biçiminde metinde geçiyor mu."""
    whole, frac = f"{amount:.2f}".split(".")
    tr = f"{int(whole):,}".replace(",", ".")
    return f"{tr},{frac}" in text or (frac == "00" and tr in text)


def validate_facts(facts: ExtractedFacts, decision_text: str) -> tuple[ExtractedFacts, list[str]]:
    """Geçersiz alanları None yapar, uyarı listesi döner."""
    warnings: list[str] = []
    text = _norm(decision_text)

    def drop(name: str, reason: str) -> None:
        setattr(facts, name, None)
        facts.evidence.pop(name, None)
        warnings.append(f"{name}: {reason}")

    # 1) aralık ve enum
    for name in ("plaintiff_fault", "defendant_fault", "disability_rate"):
        v = getattr(facts, name)
        if v is not None and not 0 <= v <= 1:
            drop(name, "0-1 aralığı dışında")
    if facts.outcome is not None and facts.outcome not in ALLOWED_OUTCOMES:
        drop("outcome", "izin verilmeyen değer")

    # 2) alıntı var mı ve metinde birebir geçiyor mu
    for name in SIMPLE_FIELDS:
        if getattr(facts, name) is None:
            continue
        quote = facts.evidence.get(name)
        if not quote:
            drop(name, "dayanak cümle yok")
        elif _norm(quote) not in text:
            drop(name, "dayanak cümle karar metninde bulunamadı")
        # 2b) yaralanma tanımı dayanak cümlede geçmeli (uydurmayı yakalar)
    if facts.injury_type is not None:
        quote = facts.evidence.get("injury_type", "")
        if _norm(facts.injury_type).lower() not in _norm(quote).lower():
            drop("injury_type", "değer dayanak cümlede geçmiyor") 

    # 3) kusur toplamı
    p, d = facts.plaintiff_fault, facts.defendant_fault
    if p is not None and d is not None and abs(p + d - 1) > 0.01:
        drop("plaintiff_fault", "kusur toplamı 1 değil")
        drop("defendant_fault", "kusur toplamı 1 değil")

    # 4) hükmedilen kalemler
    for item, amount in list(facts.awarded_items.items()):
        key = f"awarded_items.{item}"
        quote = facts.evidence.get(key)
        reason = None
        if item not in ALLOWED_ITEMS:
            reason = "izin verilmeyen kalem"
        elif amount < 0:
            reason = "negatif tutar"
        elif not quote or _norm(quote) not in text:
            reason = "dayanak cümle yok veya metinde bulunamadı"
        elif not _amount_in(quote, amount):
            reason = "tutar dayanak cümlede geçmiyor"
        if reason:
            del facts.awarded_items[item]
            facts.evidence.pop(key, None)
            warnings.append(f"{key}: {reason}")

    return facts, warnings