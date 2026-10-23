"""2. Adım (anonymize): Karar metinlerindeki kişisel verileri (KVKK) maskeler.

Maskelenen kalıplar:
- [TCKN]    : 11 haneli T.C. Kimlik Numarası
- [IBAN]    : TR ile başlayan IBAN numaraları
- [EPOSTA]  : E-posta adresleri
- [TELEFON] : Türkiye telefon numaraları
- [PLAKA]   : Araç plakaları (01-81 il kodlu)
- [ADRES]   : Mahalle, cadde, sokak, kapı no içeren açık adres kalıpları
- [KİŞİ]    : Kural + Türkçe isim sözlüğü + hukuki rol bağlamı + kısaltılmış isimler (örn. "Gamze V.")

Korunan kalıplar:
- Esas/Karar numaraları (örn. 2023/11230), para tutarları (örn. 215.180,20 TL),
  tarihler (örn. 14.12.2023), mahkeme/kurum/kanun adları ve bölüm başlıkları.
"""
from __future__ import annotations

import re
from pathlib import Path

# 1. IBAN: TR + 2 kontrol basamağı + 22 alfanümerik karakter (boşluklu veya bitişik)
_IBAN_RE = re.compile(
    r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b|\bTR\d{24}\b",
    re.IGNORECASE,
)

# 2. E-posta
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# 3. T.C. Kimlik No: İlk hanesi 0 olmayan 11 haneli bağımsız sayı.
# Tutarlarla veya tarih/esas numaralarıyla karışmaması için önünde/arkasında '.', '/', ',' olmamalı.
_TCKN_RE = re.compile(
    r"(?<![\d.,/])\b[1-9]\d{10}\b(?![\d.,/])"
)

# 4. Telefon Numarası: +90 / 05xx / 02xx / 03xx / 04xx biçimleri
# Esas/karar no (2023/11230) ve para tutarları ile çakışmaması için sıkı sınırlar.
_PHONE_RE = re.compile(
    r"(?<![\d.,/])(?:\+90\s?|0)(?:5\d{2}|[234]\d{2})[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}\b(?![\d.,/])"
)

# 5. Araç Plakası: 01 - 81 arası il kodu + 1-3 büyük harf + 2-5 rakam
# "4. Hukuk" veya "2023/11230 E." ile karışmaması için harfler yalnız Türkçe/ASCII plaka harfleri olmalı.
_PLATE_RE = re.compile(
    r"(?<![\d/])\b(?:0[1-9]|[1-7]\d|8[01])\s+[A-ZÇĞİÖŞÜ]{1,3}\s+\d{2,5}\b(?=\s+(?:plakalı|sayılı\s+plaka)|[.,;)\s]|$)"
)

# 6. Açık Adres: "... Mah. ... Cad./Sok./Bulvarı ... No: X ..." kalıbı
_ADDRESS_RE = re.compile(
    r"\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+){0,2}\s+"
    r"(?:Mahallesi|Mah\.?)\s+[^\n;]{3,100}?\b(?:No|Kapı\s*No)\s*:\s*[\w/-]+"
    r"(?:\s+[A-ZÇĞİÖŞÜa-zçğıöşü]+(?:/[A-ZÇĞİÖŞÜa-zçğıöşü]+)?)?",
)

# Kişi adı olarak ASLA maskelenmemesi gereken mahkeme, kurum, hukuk ve başlık kelimeleri
_PROTECTED_WORDS: set[str] = {
    "Yargıtay", "Hukuk", "Dairesi", "Ceza", "Danıştay", "Mahkemesi", "Mahkeme",
    "Asliye", "Ticaret", "Bölge", "Adliye", "Sulh", "İcra", "Tüketici", "İş",
    "Adli", "Tıp", "Kurumu", "Genel", "Kurulu", "Başkanlığı", "Bakanlığı",
    "Cumhuriyet", "Başsavcılığı", "Sigorta", "Tahkim", "Komisyonu", "Sosyal",
    "Güvenlik", "Kurumu", "Türk", "Borçlar", "Kanunu", "Karayolları", "Trafik",
    "Medeni", "Usul", "Muhakemeleri", "Anayasa", "Esas", "Karar", "No", "Tarih",
    "Dava", "Cevap", "Gerekçe", "Hüküm", "Sonuç", "Temyiz", "İstinaf", "İlk",
    "Derece", "Bilirkişi", "Raporu", "Kusur", "Oranı", "Maddi", "Manevi",
    "Tazminat", "Sürekli", "Geçici", "Göremezlik", "Tedavi", "Bakıcı", "Gideri",
    "Ankara", "İstanbul", "İzmir", "Bursa", "Antalya", "Adana", "Konya", "Gaziantep",
    "Şanlıurfa", "Kocaeli", "Mersin", "Diyarbakır", "Hatay", "Manisa", "Kayseri",
    "Samsun", "Balıkesir", "Kahramanmaraş", "Van", "Aydın", "Tekirdağ", "Sakarya",
    "Denizli", "Muğla", "Eskişehir", "Trabzon", "Ordu", "Erzurum", "Malatya",
    "Afyonkarahisar", "Sivas", "Tokat", "Zonguldak", "Çorum", "Kütahya", "Çanakkale",
}

# Yaygın Türkçe ilk isimler sözlüğü (kural + isim listesi birlikte çalışması için)
_COMMON_FIRST_NAMES: set[str] = {
    "Ahmet", "Mehmet", "Mustafa", "Ali", "Hüseyin", "Hasan", "İbrahim", "İsmail",
    "Osman", "Yusuf", "Murat", "Ömer", "Ramazan", "Halil", "Süleyman", "Abdullah",
    "Mahmut", "Salih", "Kemal", "Recep", "Sinan", "Metin", "Adem", "Fatih",
    "Hakan", "Serkan", "Gökhan", "Burak", "Emre", "Can", "Cem", "Eren", "Kaan",
    "Orhan", "Yaşar", "Bekir", "Musa", "Veli", "Kadir", "Celal", "Şükrü", "일",
    "Fatma", "Ayşe", "Emine", "Hatice", "Zeynep", "Elif", "Meryem", "Şerife",
    "Zehra", "Sultan", "Hanife", "Merve", "Havva", "Zeliha", "Esra", "Fadime",
    "Özlem", "Hacer", "Melek", "Yasemin", "Rabia", "Hülya", "Cemile", "Sevim",
    "Gülsüm", "Leyla", "Dilek", "Büşra", "Aysel", "Songül", "Kübra", "Gamze",
    "Filiz", "Aslı", "Seda", "Pınar", "Sibel", "Arzu", "Yıldız", "Tuğba",
    "Nuri", "Cengiz", "Levent", "Bülent", "Erkan", "Volkan", "Tolga", "Onur",
    "Uğur", "Barış", "Deniz", "Derya", "Selin", "Cansu", "Gizem", "Ebru",
}

# 7a. Yargıtay kararlarındaki kısaltılmış isim kalıpları: "Gamze V." veya "A. B." / "H. K."
# (Romen rakamları I., IV., V. ve harf başlıkları A. Gerekçe ile karışmaması için satır ortasında aranır)
_ABBREV_NAME_RE = re.compile(
    r"(?<!^)(?<!\n)\b(?:"
    r"(?:[A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,15})\s+[A-ZÇĞİÖŞÜ]\."
    r"|"
    r"[A-ZÇĞİÖŞÜ]\.\s*[A-ZÇĞİÖŞÜ]\."
    r")"
)

# 7b. Hukuki rol bağlamından hemen sonra gelen Ad Soyad (örn. "Davacı Ahmet Yılmaz", "Av. Mehmet Kaya")
_ROLE_CONTEXT_NAME_RE = re.compile(
    r"\b(Davacı|Davalı|Vekili|Av\.|Avukat|Sürücü|Sigortalı|İşleten|Müteveffa|Muris|Tanık|Mağdur)"
    r"(\s+sürücü|\s+vekili|\s+şirket)?\s+"
    r"([A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,15}(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,15})?\s+[A-ZÇĞİÖŞÜa-zçğıöşü]{2,18})\b"
)

# 7c. İsim sözlüğündeki bir ad + Büyük harfle başlayan soyad (bağlamdan bağımsız yakalama)
_CAPITALIZED_PAIR_RE = re.compile(
    r"\b([A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,15})(?:\s+([A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,15}))?\s+([A-ZÇĞİÖŞÜ][A-Za-zçğıöşüÇĞİÖŞÜ]{2,18})\b"
)


def _is_protected_phrase(words: list[str]) -> bool:
    """Kelime grubunun içinde mahkeme/kurum/hukuk terimi olup olmadığını denetler."""
    return any(w in _PROTECTED_WORDS for w in words)


def _replace_role_context_name(match: re.Match[str]) -> str:
    role = match.group(1)
    sub_role = match.group(2) or ""
    full_name = match.group(3)
    words = full_name.split()
    if _is_protected_phrase(words):
        return match.group(0)
    return f"{role}{sub_role} [KİŞİ]"


def _replace_dictionary_name(match: re.Match[str]) -> str:
    first = match.group(1)
    middle = match.group(2)
    last = match.group(3)
    words = [w for w in (first, middle, last) if w]
    if _is_protected_phrase(words):
        return match.group(0)
    if first in _COMMON_FIRST_NAMES or (middle and middle in _COMMON_FIRST_NAMES):
        return "[KİŞİ]"
    return match.group(0)


def _replace_abbrev_name(match: re.Match[str]) -> str:
    text = match.group(0)
    first_word = text.split()[0].rstrip(".")
    if first_word in _PROTECTED_WORDS or first_word in ("I", "II", "III", "IV", "V", "VI"):
        return text
    # "E." veya "K." (Esas / Karar kısaltması) ise dokunma
    if text.replace(" ", "") in ("E.", "K."):
        return text
    return "[KİŞİ]"


def anonymize_text(text: str) -> str:
    """Metindeki kişisel verileri sabit etiketlerle ([KİŞİ], [TCKN], [PLAKA] vb.) maskeler (idempotent)."""
    if not text:
        return ""

    result = text

    # 1. Yapısal kişisel veriler (IBAN, E-posta, TCKN, Telefon, Plaka, Adres)
    result = _IBAN_RE.sub("[IBAN]", result)
    result = _EMAIL_RE.sub("[EPOSTA]", result)
    result = _TCKN_RE.sub("[TCKN]", result)
    result = _PHONE_RE.sub("[TELEFON]", result)
    result = _PLATE_RE.sub("[PLAKA]", result)
    result = _ADDRESS_RE.sub("[ADRES]", result)

    # 2. Kişi adları (Rol bağlamı -> İsim sözlüğü -> Kısaltılmış isimler)
    result = _ROLE_CONTEXT_NAME_RE.sub(_replace_role_context_name, result)
    result = _CAPITALIZED_PAIR_RE.sub(_replace_dictionary_name, result)
    result = _ABBREV_NAME_RE.sub(_replace_abbrev_name, result)

    # 3. Ardışık oluşan "[KİŞİ] [KİŞİ]" tekrarlarını tek "[KİŞİ]" etiketine indir (idempotency)
    result = re.sub(r"\[KİŞİ\](?:\s+\[KİŞİ\])+", "[KİŞİ]", result)

    return result


def anonymize_file(input_path: Path, output_path: Path) -> Path:
    """Tek bir karar dosyasını anonimleştirip hedef yola yazar (idempotent)."""
    raw_text = input_path.read_text(encoding="utf-8")
    masked = anonymize_text(raw_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(masked, encoding="utf-8", newline="\n")
    return output_path


def run_anonymize_dir(input_dir: Path, output_dir: Path) -> list[Path]:
    """Verilen klasördeki tüm karar_*.txt dosyalarını anonimleştirip hedef klasöre yazar."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for src in sorted(input_dir.glob("karar_*.txt")):
        dst = output_dir / src.name
        written.append(anonymize_file(src, dst))
    return written