"""topic_filter.py: Kararları dava türlerine ve sonuçlarına göre ayrıştırır."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from trafikrag.ingestion.steps.parse_decision import extract_metadata, split_sections


@dataclass
class FilterResult:
    karar_id: str
    kabul_edildi: bool
    sebep: str
    konu_etiketi: str
    sonuc: str


def _tr_lower(text: str) -> str:
    return text.replace("İ", "i").replace("I", "ı").lower()


# İlgili tazminat kalemi anahtar kelimeleri
_ISCILIK_RE = re.compile(
    r"sürekli\s+iş\s*göremezlik|geçici\s+iş\s*göremezlik|iş\s+gücü\s+kaybı|maluliyet|meslekte\s+kazanma\s+gücü",
    re.IGNORECASE,
)
_TEDAVI_RE = re.compile(r"tedavi\s+gider|hastane\s+gider|ilaç\s+gider|iyileşme\s+gider", re.IGNORECASE)
_BAKICI_RE = re.compile(r"bakıcı\s+gider|bakım\s+gider", re.IGNORECASE)
_DESTEK_RE = re.compile(r"destekten\s+yoksun\s+kalma", re.IGNORECASE)

# Kusur / bilirkişi / oran varlığı kontrolü
_KUSUR_OR_EXPERT_RE = re.compile(
    r"kusur|bilirkişi|adli\s+tıp|maluliyet\s+oran|%\s*\d+|\d+\s*oranında",
    re.IGNORECASE,
)

# Elenen konular (tutanak iptali, sadece araç hasarı/kasko)
_TUTANAK_IPTALI_RE = re.compile(r"kaza\s+tespit\s+tutanağ\w*\s+iptali", re.IGNORECASE)
_ARAC_HASARI_RE = re.compile(
    r"kasko|araç\s+hasar|değer\s+kaybı|ikame\s+araç|kazanç\s+kaybı",
    re.IGNORECASE,
)
_USUL_ONLY_RE = re.compile(
    r"görevsizlik|yetkisizlik|merci\s+tayini|yargı\s+yolu\s+caiz\s+olmadığından",
    re.IGNORECASE,
)


def detect_outcome(text: str) -> str:
    """Kararın sonuç bölümünden (hüküm) net sonucu çıkarır: kabul | kismen_kabul | ret | bozma | istinaf_reddi | kaldirma | belirsiz."""
    sections = split_sections(text)
    hukum_texts = [s.text for s in sections if s.kind == "hukum"]
    
    # Hüküm penceresi 1500'den 4000 karaktere çıkarıldı
    target = _tr_lower("\n".join(hukum_texts) if hukum_texts else text[-4000:])

    # 1. İstinaf/Başvuru Esastan Red (Araya madde girebilme toleransı eklendi)
    istinaf_red_pattern = r"(?:istinaf|başvuru)\w*.{0,150}?esastan\s+reddine"
    if re.search(istinaf_red_pattern, target, re.IGNORECASE | re.DOTALL):
        return "istinaf_reddi"

    if "kaldırılmasına" in target and "hüküm kurulmasına" in target:
        return "kaldirma"
        
    if "bozulmasına" in target or "bozma" in target:
        return "bozma"
        
    # Onama, istinaf_reddi'ne eşlendi
    if "onanmasına" in target or "onama" in target or "onamasına" in target or "onaylanmasına" in target:
        return "istinaf_reddi"
        
    # Çok maddeli kararlar için regex desteği
    if "kısmen kabul" in target or re.search(r"\d+-\s*davanın\s+kısmen\s+kabulü", target, re.IGNORECASE):
        return "kismen_kabul"
        
    if "davanın kabulüne" in target or "kabulüne" in target or re.search(r"\d+-\s*davanın\s+kabulü", target, re.IGNORECASE):
        return "kabul"
        
    if "davanın reddine" in target or "istemin reddine" in target or "reddine" in target:
        return "ret"
        
    return "belirsiz"


def evaluate_decision(karar_id: str, text: str) -> FilterResult:
    """Tek bir karar metnini güncel proje kriterlerine göre değerlendirir."""
    lower = _tr_lower(text)
    # Künye kontrolü için sadece ilk 1000 karakter alınır (emsal atıflarını tolere etmek için)
    header = _tr_lower(text[:1000])
    
    meta = extract_metadata(text)
    court = meta.get("court", "")
    sonuc = detect_outcome(text)

    # 1. Ceza Dairesi veya Danıştay kontrolü (Sadece künye)
    if "ceza dairesi" in header or "danıştay" in header:
        return FilterResult(karar_id, False, "mahkeme_uyumsuz_ceza_veya_danistay", "elenen", sonuc)

    # 2. Mahkeme kontrolü (Eski katı 4/17 HD kısıtı esnetildi, künyeye ve metne göre esnek denetleniyor)
    # Artık BAM, İlk Derece ve Yargıtay kararları destekleniyor, mahkeme bilgisi etiket olarak tutuluyor.

    # 3. Kaza tespit tutanağı iptali kontrolü
    if _TUTANAK_IPTALI_RE.search(lower) and not _ISCILIK_RE.search(lower):
        return FilterResult(karar_id, False, "kapsam_disi_tutanak_iptali", "elenen", sonuc)

    # 4. Konu etiketlerini çıkar
    tags: list[str] = []
    
    # Mahkeme düzeyini etiket olarak ekle
    if court:
        tags.append(f"mahkeme_{_tr_lower(court).replace(' ', '_')}")

    has_iscilik = bool(_ISCILIK_RE.search(lower))
    has_tedavi = bool(_TEDAVI_RE.search(lower))
    has_bakici = bool(_BAKICI_RE.search(lower))
    has_destek = bool(_DESTEK_RE.search(lower))
    has_kusur = bool(_KUSUR_OR_EXPERT_RE.search(lower))

    if has_iscilik:
        tags.append("iscilik")
    if has_tedavi:
        tags.append("tedavi")
    if has_bakici:
        tags.append("bakici")
    if has_kusur:
        tags.append("kusur")
    if has_destek:
        tags.append("destek")

    # Tarih etiketi (2020 öncesi içtihat kontrolü)
    date_str = meta.get("date", "")
    if date_str and len(date_str) >= 4 and date_str[:4].isdigit():
        if int(date_str[:4]) <= 2020:
            tags.append("2020_oncesi")

    # Sonuç etiketini oluştur
    if sonuc == "belirsiz":
        tags.append("sonuc_belirsiz")
    else:
        tags.append(f"sonuc_{sonuc}")

    tag_str = "|".join(tags) if tags else "belirsiz"

    # 5. Ölümlü kaza (destekten yoksun kalma) kontrolü: Silinmez, ayrı loglanır/saklanır (olumlu -> ölümlü düzeltildi)
    if has_destek and not (has_iscilik or has_tedavi or has_bakici):
        return FilterResult(karar_id, False, "kapsam_disi_ölümlü_destek_ayri_sakla", "destek", sonuc)

    # 6. Sadece kasko / araç hasarı / değer kaybı kontrolü (bedensel zarar yoksa elenir)
    if _ARAC_HASARI_RE.search(lower) and not (has_iscilik or has_tedavi or has_bakici):
        return FilterResult(karar_id, False, "kapsam_disi_sadece_arac_hasari_kasko", "elenen", sonuc)

    # 7. Yaralanmalı maddi tazminat kalemi var mı?
    if not (has_iscilik or has_tedavi or has_bakici):
        if _USUL_ONLY_RE.search(lower):
            return FilterResult(karar_id, False, "kapsam_disi_sadece_usul", "elenen", sonuc)
        return FilterResult(karar_id, False, "yaralanmali_maddi_tazminat_kalemi_yok", "elenen", sonuc)

    # 8. Kusur / maluliyet / bilirkişi bilgisi kontrolü
    if not has_kusur:
        return FilterResult(karar_id, False, "eksik_icerik_kusur_veya_bilirkisi_yok", tag_str, sonuc)

    # ARTIK SONUCU BELİRSİZ OLANLAR ELENMİYOR
    return FilterResult(karar_id, True, "kabul_yaralanmali_maddi_tazminat", tag_str, sonuc)


def write_selection_log(results: list[FilterResult], log_path: Path) -> Path:
    """Değerlendirme sonuçlarını selection_log.csv dosyasına yazar (idempotent)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", newline="\n") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["karar_id", "kabul_edildi", "sebep", "konu_etiketi", "sonuc"])
        for r in results:
            writer.writerow([r.karar_id, r.kabul_edildi, r.sebep, r.konu_etiketi, r.sonuc])
    return log_path


def run_topic_filter(
    input_dir: Path,
    output_dir: Path,
    log_path: Path | None = None,
    rejected_dir: Path | None = None,
) -> list[Path]:
    """Klasördeki kararları filtreler; kabul edilenleri output_dir'e, ölümlü/özel durumdakileri ayrı klasöre yazar ve CSV log üretir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if rejected_dir is not None:
        rejected_dir.mkdir(parents=True, exist_ok=True)

    if log_path is None:
        log_path = output_dir.parent / "selection_log.csv"

    results: list[FilterResult] = []
    accepted_paths: list[Path] = []
    accepted_ids: set[str] = set()

    for src in sorted(input_dir.glob("*.txt")):
        text = src.read_text(encoding="utf-8")
        res = evaluate_decision(src.stem, text)
        results.append(res)
        
        if res.kabul_edildi:
            accepted_ids.add(src.stem)
            dst = output_dir / src.name
            if dst.resolve() != src.resolve():
                dst.write_text(text, encoding="utf-8", newline="\n")
            accepted_paths.append(dst)
        else:
            # Ölümlü (destek) kararlar silinmez, ayrı klasörde/logda saklanır
            if res.sebep == "kapsam_disi_ölümlü_destek_ayri_sakla" and rejected_dir is not None:
                rej_dst = rejected_dir / src.name
                rej_dst.write_text(text, encoding="utf-8", newline="\n")

    # Idempotency: hedef klasörde kalmış eski reddedilen dosyaları temizle
    if output_dir.resolve() != input_dir.resolve():
        for existing in output_dir.glob("*.txt"):
            if existing.stem not in accepted_ids:
                existing.unlink()

    write_selection_log(results, log_path)
    return accepted_paths