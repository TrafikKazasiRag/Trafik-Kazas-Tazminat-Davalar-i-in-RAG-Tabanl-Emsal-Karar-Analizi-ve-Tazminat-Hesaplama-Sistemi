"""1. Adım (clean): Ham karar metinlerindeki site gürültüsünü temizler ve metni normalleştirir.

Kurallar:
- Site reklamları, menüler, telif uyarıları, editoryal özetler ve site yorumları silinir.
- Normal karar cümlelerinin (örn. "fazlaya ilişkin tüm hakları saklıdır", "1/2", "15")
  yanlışlıkla silinmemesi için gürültü kalıpları yalnızca kısa satırlara (<120 karakter)
  veya tam satır (^...$) eşleşmelerine uygulanır.
- Unicode NFC normalleştirmesi yapılır, zero-width karakterler (\u200b) silinir,
  bölünemez boşluklar (\u00a0) normal boşluğa çevrilir.
- Başlıklar (I. DAVA, II. CEVAP, IV. GEREKÇE, C. Gerekçe, V. KARAR, VI. KARAR, SONUÇ :)
  ve künye bilgileri KESİNLİKLE aynı satırda ve yazımla korunur, satırlar birleştirilmez.
- Adım idempotent'tir.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

# Görünmez sıfır genişlikli karakterler silinir (\u200b), \u00a0 ise normal boşluğa çevrilir.
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\u00ad]")

# Satır içi birden fazla boşluk veya sekme (tab)
_MULTI_SPACE_RE = re.compile(r"[ \t]+")

# 3 veya daha fazla ardışık satır sonunu en fazla 2 satır sonuna indirmek için
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

# Gürültü kontrolünün uygulanacağı maksimum satır uzunluğu (uzun karar cümlelerini korumak için)
MAX_NOISE_LINE_LENGTH = 120

# Madde 2: Yalnızca "Sayfa 1 / 3", "Sayfa 2" ve "- 3 -" gibi açık sayfa numarası kalıpları silinir.
# Tek başına duran "15" veya "1/2" (maluliyet/pay oranı) KESİNLİKLE silinmez.
_PAGE_NUMBER_LINE_RE = re.compile(
    r"^(?:sayfa\s*\d+(?:\s*/\s*\d+)?|-\s*\d+\s*-)$",
    re.IGNORECASE,
)

# Breadcrumb / navigasyon satırları (örn. "Anasayfa > Yargıtay Kararları > ...")
_BREADCRUMB_LINE_RE = re.compile(r"^(?:ana\s*sayfa|anasayfa|home)\s*[>/»|].*$", re.IGNORECASE)

# Madde 1 & 19: Daraltılmış site gürültüsü kalıpları (NOISE_PATTERNS).
# Yalnızca kısa satırlarda (<120 karakter) ve spesifik site/reklam bağlamlarında eşleşir.
NOISE_PATTERNS: list[re.Pattern[str]] = [
    # Tıklama ve reklam çağrıları
    re.compile(r"^.*\b(?:tıklayınız|tiklayiniz)\b.*$", re.IGNORECASE),
    re.compile(r"^reklam\s*:?$", re.IGNORECASE),
    re.compile(r"^ilgili\s+kararlar\s*:?$", re.IGNORECASE),
    re.compile(r"^benzer\s+kararlar\s*:?$", re.IGNORECASE),
    re.compile(r"^etiketler\s*:.*$", re.IGNORECASE),
    re.compile(r"^paylaş\s*:.*$", re.IGNORECASE),
    re.compile(r"^yazdır$", re.IGNORECASE),
    re.compile(r"^https?://\S+$", re.IGNORECASE),

    # Minval Hukuk ve avukat reklam başlıkları (mahkeme cümlesi olmayan kısa başlık/etiket satırları)
    # "Davalı Minval Hukuk Sigorta A.Ş. vekili temyiz etti." veya "Davacı vekili Ankara Avukat..." korunur.
    re.compile(r"^kararın\s+özeti\s*;.*$", re.IGNORECASE),
    re.compile(
        r"^(?:[\w\sçğıöşüÇĞİÖŞÜ]+\s*[-–|]\s*)?minval\s+hukuk(?:\s+bürosu|\s+danışmanlık)?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:ankara|istanbul|izmir)\s+avukat(?:\s*[-–|:]\s*.*|\s+bürosu.*)?$",
        re.IGNORECASE,
    ),

    # Kanunyolu ve editoryal blok başlıkları
    re.compile(r"^karar\s+özeti\s+ve\s+hukuki\s+bağlam\s*:?$", re.IGNORECASE),
    re.compile(r"^(?:kaynak\s*:\s*)?(?:www\.)?kanun\s*yolu\.com(?:\.tr)?.*$", re.IGNORECASE),
    re.compile(r"^(?:kaynak\s*:\s*)?(?:www\.)?yargitaykararlari\.com(?:\.tr)?.*$", re.IGNORECASE),

    # Karamercan Hukuk ve telif/not blokları
    # "Davacının tüm hakları saklıdır, fazlaya ilişkin..." gibi cümleler korunur;
    # yalnızca telif/kopyalama/© içeren veya tek başına duran telif satırları silinir.
    re.compile(r"^.*\bkaramercan\s+hukuk\b.*$", re.IGNORECASE),
    re.compile(r"^.*kaynak\s+gösterilmeden\s+(?:kopyalana?maz|kullanılamaz).*$", re.IGNORECASE),
    re.compile(
        r"^(?:tüm\s+hakları\s+saklıdır\.?(?:\s*©.*)?|.*(?:©|copyright).*tüm\s+hakları\s+saklıdır.*)$",
        re.IGNORECASE,
    ),
    re.compile(r"^bu\s+karar\s+.*tarafından\s+derlenmiştir\.?$", re.IGNORECASE),
    # Yalnızca BÜYÜK HARFLİ "BİLGİ :" veya "B İ L G İ :" dipnotları silinir (re.IGNORECASE yok!).
    # Böylece "Bilgi : bilirkişi raporu dosyaya sunulmuştur." satırı korunur.
    re.compile(r"^(?:B\s+İ\s+L\s+G\s+İ|BİLGİ)\s*:.*$"),
]

# Korunması zorunlu bölüm başlıkları
_PROTECTED_HEADING_RE = re.compile(
    r"^(?:[IVX]+\.\s+.{2,60}|[A-ZÇĞİÖŞÜ]\.\s+.{2,60}|SONUÇ\s*:.*)$"
)


def _is_noise_line(line: str) -> bool:
    """Satırın gürültü olup olmadığını kontrol eder."""
    if not line:
        return False
    if _PROTECTED_HEADING_RE.match(line):
        return False
    if _PAGE_NUMBER_LINE_RE.match(line):
        return True
    if _BREADCRUMB_LINE_RE.match(line):
        return True
    # Madde 1: Uzun karar cümlelerini silmemek için gürültü kalıpları yalnızca kısa satırlara uygulanır
    if len(line) >= MAX_NOISE_LINE_LENGTH:
        return False
    for pattern in NOISE_PATTERNS:
        if pattern.match(line):
            return True
    return False


def clean_text(text: str) -> str:
    """Ham karar metnini temizler, başlıkları ve satır yapısını korur, idempotency sağlar."""
    if not text:
        return ""

    # 1. Unicode NFC normalleştirmesi ve görünmez/bölünemez karakter dönüşümleri
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u00a0", " ")  # Non-breaking space -> normal boşluk
    normalized = _ZERO_WIDTH_RE.sub("", normalized)  # Zero-width silinir

    # 2. Satır satır işleme (satırlar birleştirilmez, kendi satırında kalır)
    cleaned_lines: list[str] = []
    for raw_line in normalized.split("\n"):
        line = _MULTI_SPACE_RE.sub(" ", raw_line).strip()

        if _is_noise_line(line):
            continue

        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines)
    result = _MULTI_NEWLINE_RE.sub("\n\n", result).strip()

    return result + "\n" if result else ""


def clean_file(input_path: Path, output_path: Path) -> Path:
    """Tek bir dosyayı temizleyip hedef yola yazar (Ham dosya değişmez)."""
    raw_text = input_path.read_text(encoding="utf-8")
    cleaned = clean_text(raw_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(cleaned, encoding="utf-8", newline="\n")
    return output_path


def run_clean_dir(input_dir: Path, output_dir: Path) -> list[Path]:
    """data/raw/ klasöründen okuyup data/interim/ klasörüne yazar."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for src in sorted(input_dir.glob("karar_*.txt")):
        dst = output_dir / src.name
        written.append(clean_file(src, dst))
    return written