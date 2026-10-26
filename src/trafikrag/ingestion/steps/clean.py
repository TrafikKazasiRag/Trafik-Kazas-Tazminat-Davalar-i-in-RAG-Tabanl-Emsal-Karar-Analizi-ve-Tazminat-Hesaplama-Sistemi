"""1. Adım (clean): Ham karar metinlerindeki site gürültüsünü temizler ve metni normalleştirir.

Kurallar:
- Site reklamları, menüler, telif uyarıları, editoryal özetler ve site yorumları silinir.
- Normal karar cümlelerinin (örn. "fazlaya ilişkin tüm hakları saklıdır", "1/2", "15")
  yanlışlıkla silinmemesi için gürültü kalıpları yalnızca kısa satırlara (<120 karakter)
  veya tam satır (^...$) eşleşmelerine uygulanır.
- Unicode NFC normalleştirmesi yapılır, zero-width karakterler (\u200b vb.) silinir,
  bölünemez boşluklar (\u00a0) normal boşluğa çevrilir.
- Başlıklar (I. DAVA, II. CEVAP, IV. GEREKÇE, C. Gerekçe, V. KARAR, VI. KARAR, SONUÇ :)
  ve künye bilgileri KESİNLİKLE aynı satırda ve yazımla korunur, satırlar birleştirilmez.
- Adım idempotent'tir.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

# Görünmez sıfır genişlikli karakterler silinir (\u200b, \ufeff vb.), \u00a0 normal boşluğa çevrilir.
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\u00ad]")

# Satır içi birden fazla boşluk veya sekme (tab)
_MULTI_SPACE_RE = re.compile(r"[ \t]+")

# 3 veya daha fazla ardışık satır sonunu en fazla 2 satır sonuna indirmek için
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

# Gürültü kontrolünün uygulanacağı maksimum satır uzunluğu (uzun karar cümlelerini korumak için)
MAX_NOISE_LINE_LENGTH = 120

# Açık sayfa numarası kalıpları (örn. "Sayfa 1 / 3", "Sayfa 2", "- 3 -", "[Sayfa 1]")
_PAGE_NUMBER_LINE_RE = re.compile(
    r"^(?:sayfa\s*\d+(?:\s*/\s*\d+)?|\[?\s*sayfa\s*\d+\s*\]?|-\s*\d+\s*-)$",
    re.IGNORECASE,
)

# Breadcrumb / navigasyon satırları (örn. "Anasayfa > Yargıtay Kararları > ...")
_BREADCRUMB_LINE_RE = re.compile(r"^(?:ana\s*sayfa|anasayfa|home)\s*[>/»|].*$", re.IGNORECASE)

# Daraltılmış site gürültüsü kalıpları (NOISE_PATTERNS).
NOISE_PATTERNS: list[re.Pattern[str]] = [
    # Tıklama ve reklam çağrıları
    re.compile(r"\b(?:tıklayınız|tiklayiniz)\b", re.IGNORECASE),
    re.compile(r"^reklam\s*:?$", re.IGNORECASE),
    re.compile(r"^ilgili\s+(?:kararlar|içtihatlar)\s*:?$", re.IGNORECASE),
    re.compile(r"^benzer\s+(?:kararlar|içtihatlar)\s*:?$", re.IGNORECASE),
    re.compile(r"^etiketler\s*:.*$", re.IGNORECASE),
    re.compile(r"^paylaş\s*:.*$", re.IGNORECASE),
    re.compile(r"^yazdır$", re.IGNORECASE),
    re.compile(r"^https?://\S+$", re.IGNORECASE),

    # Hukuk bürosu ve avukat reklam başlıkları (kısa etiket satırları)
    re.compile(r"^kararın\s+özeti\s*;.*$", re.IGNORECASE),
    re.compile(
        r"^(?:[\w\sçğıöşüÇĞİÖŞÜ]+\s*[-–|]\s*)?minval\s+hukuk(?:\s+bürosu|\s+danışmanlık)?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:ankara|istanbul|izmir|bursa|antalya)\s+avukat(?:\s*[-–|:]\s*.*|\s+bürosu.*)?$",
        re.IGNORECASE,
    ),

    # Kanunyolu, içtihat siteleri ve editoryal blok başlıkları
    re.compile(r"^karar\s+özeti\s+ve\s+hukuki\s+bağlam\s*:?$", re.IGNORECASE),
    re.compile(r"^(?:kaynak\s*:\s*)?(?:www\.)?[\w-]+\.(?:com|net|org|gov|edu)(?:\.tr)?.*$", re.IGNORECASE),

    # Telif ve kopyalama engeli blokları
    re.compile(r"^.*\bkaramercan\s+hukuk\b.*$", re.IGNORECASE),
    re.compile(r"^.*kaynak\s+gösterilmeden\s+(?:kopyalana?maz|kullanılamaz).*$", re.IGNORECASE),
    re.compile(
        r"^(?:tüm\s+hakları\s+saklıdır\.?(?:\s*©.*)?|.*(?:©|copyright).*tüm\s+hakları\s+saklıdır.*)$",
        re.IGNORECASE,
    ),
    re.compile(r"^bu\s+karar\s+.*tarafından\s+derlenmiştir\.?$", re.IGNORECASE),
    
    # Yalnızca BÜYÜK HARFLİ "BİLGİ :" veya "B İ L G İ :" dipnotları silinir (re.IGNORECASE yok!).
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
    if len(line) >= MAX_NOISE_LINE_LENGTH:
        return False
    for pattern in NOISE_PATTERNS:
        if pattern.search(line):  # match yerine search ile daha esnek eşleşme
            return True
    return False


def clean_text(text: str) -> str:
    """Ham karar metnini temizler, başlıkları ve satır yapısını korur, idempotency sağlar."""
    if not text:
        return ""

    # 1. Önce Unicode NFC normalleştirmesi ve sıfır genişlikli karakter temizliği yapılır
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u00a0", " ")  # Non-breaking space -> normal boşluk
    normalized = _ZERO_WIDTH_RE.sub("", normalized)  # Zero-width silinir

    # 2. Satır satır işleme (her satır kendi içinde temizlenir)
    cleaned_lines: list[str] = []
    for raw_line in normalized.split("\n"):
        line = _MULTI_SPACE_RE.sub(" ", raw_line).strip()

        if _is_noise_line(line):
            continue

        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines)
    result = _MULTI_NEWLINE_RE.sub("\n\n", result).strip()

    return result + "\n" if result else ""


def _read_file_safe(file_path: Path) -> str:
    """Dosyayı güvenli bir şekilde farklı encoding seçenekleriyle okur."""
    for enc in ("utf-8", "cp1254", "latin-1"):
        try:
            return file_path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"Dosya bilinen formatlarda okunamadı: {file_path}")


def clean_file(input_path: Path, output_path: Path) -> Path:
    """Tek bir dosyayı temizleyip hedef yola yazar (Ham dosya değişmez)."""
    raw_text = None
    for encoding in ("utf-8", "cp1254", "latin-1"):
        try:
            raw_text = input_path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue

    if raw_text is None:
        raw_text = ""

    cleaned = clean_text(raw_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(cleaned, encoding="utf-8", newline="\n")
    return output_path


def run_clean_dir(input_dir: Path, output_dir: Path) -> list[Path]:
    """input_dir klasöründen okuyup output_dir klasörüne yazar."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    # Hem karar_*.txt hem de düz *.txt dosyalarını destekleyecek esneklik
    for src in sorted(input_dir.glob("*.txt")):
        dst = output_dir / src.name
        written.append(clean_file(src, dst))
    return written